import axios from 'axios'
import ShortUniqueId from 'short-unique-id';

import { queryResponseCodes } from "./constants";
import { debugResponse } from "./debug";
import { showToast } from "./notification_control";
import { messageModalStore } from "./stores/stores_initializer";
import { emitter } from './emitter';
import { handleError } from './logging/utils';

const uid = new ShortUniqueId({dictionary: 'alpha_upper', length: 4})

let polling_busy = null;
let request_map = new Map()

function call_polling(startup) {
    polling_busy = true
    axios.post(
      '/long_polling/',
      {startup: startup}
    ).then((resp) => {
      polling_busy = false
      resp.data.returning_rows.forEach(chunk => {
        try {
          polling_response(chunk)
        } catch(err) {
          console.log(err)
        }
      });
      if (request_map.size !== 0) {
        call_polling(false)
      } else {
        polling_busy = null
      }
    })
    .catch((error) => {
      polling_busy = false
      handleError(error);
    })
}

function polling_response(message) {

  let context_code = null;
  let context = null;

  if(message.context_code) {
    let entry = request_map.get(message.context_code)
    if(entry) {
      context_code = entry.code
      context = entry.context
    }
  }

  switch(message.response_type) {
    case parseInt(queryResponseCodes.Pong): {
      websocketPong();
      break;
    }
    case parseInt(queryResponseCodes.SessionMissing): {
      messageModalStore.showAlertModal("Session not found please reload the page.");
      break;
    }
    case parseInt(queryResponseCodes.MessageException): {
      showToast("error", message.data);
      break;
    }
    case parseInt(queryResponseCodes.PasswordRequired): {
      if (context) {
        SetAcked(context);
        QueryPasswordRequired(context, message.data);
        break;
      }
    }
    case parseInt(queryResponseCodes.QueryAck): {
      if (context) {
        SetAcked(context);
        break;
      }
    }
    case parseInt(queryResponseCodes.QueryResult): {
      if (context) {
        SetAcked(context);
        if(context.simple && context.callback!=null) { //used by schema editor only, dont run any legacy rendering for simple requests
          context.callback(message)
        } else  {
          context.callback(message, context)
        }
        //Remove context
        if (!message.data.chunks || message.data.last_block || message.error) {
          removeContext(context_code)
        }

      }
      break;
    }
    case parseInt(queryResponseCodes.OperationCancelled): {
      if (context) {
        if(context.callback!=null) {
          context.callback(message)
        }
        removeContext(context_code)
      }
      break;
    }
    case parseInt(queryResponseCodes.ConsoleResult): {
      if (context) {
        context.callback(message, context)

        //Remove context
        if (message.data.last_block || message.error) {
          removeContext(context_code);
        }
      }
      break;
    }
    case parseInt(queryResponseCodes.TerminalResult): {
      if (context) {
          context.callback(message, context)
      }
      break;
    }
    case parseInt(queryResponseCodes.QueryEditDataResult): {
      if (context) {
        context.callback(message)
        removeContext(context_code);
      }
      break;
    }
    case parseInt(queryResponseCodes.SaveEditDataResult): {
      if (context) {
        context.callback(message)
        removeContext(context_code);
      }
      break;
    }
    case parseInt(queryResponseCodes.DebugResponse): {
      if (context) {
        SetAcked(context);
        debugResponse(message, context);
        if (message.data.remove_context) {
          removeContext(context_code);
        }
      }
      break;
    }
    case parseInt(queryResponseCodes.RemoveContext): {
      if (context) {
        removeContext(context_code);
      }
      break;
    }
    case parseInt(queryResponseCodes.SchemaEditResult): {
      if (context) {
        context.callback(message);
        removeContext(context_code);
      }
    }
    default: {
      break;
    }
    case parseInt(queryResponseCodes.AdvancedObjectSearchResult): {
      if (context) {
        SetAcked(context);
        advancedObjectSearchReturn(message, context);
        removeContext(context_code);
      }
      break;
    }
  }
}

function QueryPasswordRequired(context, message) {
  if(["query", "console"].includes(context.tab.metaData.mode)) {
    emitter.emit("show_password_prompt", {
      databaseIndex: context.database_index,
      successCallback: function() {
        context.passwordSuccessCallback(context)
      },
      cancelCallback: function() {
        context.passwordFailCalback()
			},
      message: message
    })
  }
}

function createContext(context) {
  let context_code = uid.seq()
  if(context.code) {
    context_code = context.code
  } else {
    context.code = context_code
  }

  request_map.set(context_code, context)

	return context;
}

function removeContext(context_code) {
  request_map.delete(context_code)
}

function createRequest(request_type, message_data, context) {
  let context_code = undefined;
	if (context != null) {
		if (typeof(context) === 'object') {
      let ctx = {
        code: context_code,
        context: context
      }
      createContext(ctx)
      context_code = ctx.code
      context.code = context_code
		}
    // if context code is passed do not create a new context
		else {
			context_code = context;
		}
	}

  // synchronize call_polling requests, do not run new one when there is a request in progress
  if (polling_busy === null)
    call_polling(true)
  else if (polling_busy === false) {
    call_polling(false)
  }

  axios.post(
    '/create_request/',
    {
      request_type: request_type,
      context_code: context_code || 0,
      data: message_data
    }
  )
}

function SetAcked(context) {
	if (context)
		context.acked = true;
}

export { createContext, createRequest, SetAcked, removeContext }