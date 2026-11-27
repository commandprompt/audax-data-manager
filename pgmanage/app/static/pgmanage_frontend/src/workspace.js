import ContextMenu from '@imengyu/vue3-context-menu'
import { startLoading } from './ajax_control'
import { emitter } from './emitter'
import { tabsStore, connectionsStore, messageModalStore } from './stores/stores_initializer.js'
import { Modal } from 'bootstrap'


/// <summary>
/// Check if there are troublesome tabs
/// </summary>
/// <param name="p_cancel_function">Ok function.</param>
/// <param name="p_ok_function">Cancel function.</param>
function checkBeforeChangeDatabase(p_cancel_function, p_ok_function) {

  for (const tab of tabsStore.selectedPrimaryTab.metaData.secondaryTabs) {
    if(["edit", "alter", "monitoring_dashboard"].includes(tab.metaData.mode)) {
      messageModalStore.showAlertHtmlModal(
        "Cannot change the active database.<br>Please close any open tabs of the following types first: <br><br><b>Edit Data<br><br>Alter Table<br><br>Monitoring Dashboard</b>"
      );
      if (p_cancel_function!=null) {
        p_cancel_function();
      }
      return false;
    }
  }

	if (p_ok_function!=null) {
    p_ok_function();
  }
  return true;
}


/// <summary>
/// Rename tab.
/// </summary>
function renameTab(tab) {

  messageModalStore.showPromptModal("", tab.name, (value) => {
    tab.name = value;
  });
}


function resizeWindow(){
	refreshHeights(true);
}


var resizeTimeout;
$(window).resize(function() {
	clearTimeout(resizeTimeout);
	resizeTimeout = setTimeout(resizeWindow, 200);
});


/// <summary>
/// Refresh divs sizes and components of the currently selected tab
/// </summary>
function refreshHeights(p_all) {
  setTimeout(function(){
    //If inner tab exists
    if (!!tabsStore.selectedPrimaryTab.metaData.secondaryTabs.length && tabsStore.selectedPrimaryTab.metaData.selectedTab) {
      let tab = tabsStore.selectedPrimaryTab.metaData.selectedTab;

      if (tab.metaData.mode === 'console') {
        emitter.emit(`${tab.id}_resize`)
      }
    }

    // Updating position of omnis.
    if (v_omnis) {
      if (v_omnis.omnis_ui_assistant) {
        v_omnis.omnis_ui_assistant.goToStep(v_omnis.omnis_ui_assistant.stepSelected);
      }
      else if (v_omnis.div) {
        v_omnis.div.style.top = v_omnis.root.getBoundingClientRect().height - 45 + 'px';
        v_omnis.div.style.left = v_omnis.root.getBoundingClientRect().width - 60 + 'px';
      }
    }

  },351);
}


function showMenuNewTabOuter(e) {
  function getConnectionInfo(conn) {
    let conn_name = "";
    let tooltip_name = "";
    let name = "";
    if (conn.public) {
      conn_name += '<i class="fas fa-users me-3" style="color:#c57dd2;"></i>';
    }
    if (conn.alias) {
      name = conn.alias;
      conn_name += `(${conn.alias})`;
      tooltip_name += `<h5 class="my-1">${conn.alias}</h5>`;
    }
    if (conn.conn_string) {
      conn_name += ` ${conn.conn_string}`;
      tooltip_name += `<div class="mb-1">${conn.conn_string}</div>`;
    } else {
      if (conn.details1) {
        conn_name += conn.details1;
        tooltip_name += `<div class="mb-1">${conn.details1}</div>`;
      }
      if (conn.details2) {
        conn_name += ` - ${conn.details2}`;
        tooltip_name += `<div class="mb-1">${conn.details2}</div>`;
      }
    }
    return [conn, conn_name, tooltip_name, name];
  }

  function createConnectionGroup(group) {
    const group_connections = connectionsStore.connections
      .filter((conn) => group.conn_list.includes(conn.id))
      .map((conn) => {
        const [_, conn_name, tooltip_name, name] = getConnectionInfo(conn);
        let icon =
          conn.technology == "terminal"
            ? "fa-terminal"
            : `node node-${conn.technology}`;
        let onClick;
        if (conn.technology == "terminal") {
          onClick = () => {
            tabsStore.createTerminalTab(conn.id, conn.alias, conn.details1)
          };
        } else {
          onClick = () => {
            tabsStore.createWorkspaceTab(conn.id, true, name, tooltip_name)
          };
        }
        return {
          label: conn_name,
          icon: `fas ${icon}`,
          onClick: onClick,
        };
      });

    return {
      label: group.name,
      icon: "fas fa-plug",
      children: group_connections,
    };
  }
  // Opening connections management when there are no configured connections.
  if (
    !connectionsStore.connections ||
    connectionsStore.connections.length === 0
  ) {
    Modal.getOrCreateInstance("#connections-modal").show()
  } else {
    let items = [];

    // Building connection list
    if (connectionsStore.connections.length > 0) {
      // No custom groups, render all connections in the same list
      if (!connectionsStore.groups.length) {
        const connectionsList = createConnectionGroup({
          name: "Connections",
          conn_list: connectionsStore.connections.map((conn) => conn.id),
        });

        items.push(connectionsList);
      }
      //Render connections split in groups
      else {
        const group_list = [
          createConnectionGroup({
            name: "All Connections",
            conn_list: connectionsStore.connections.map((conn) => conn.id),
          }),
          ...connectionsStore.groups.map(createConnectionGroup),
        ];

        items.push({
          label: "Connections",
          icon: "fas fa-plug",
          children: group_list,
        });
      }
    }

    if (connectionsStore.remote_terminals.length > 0) {
      const submenu_terminal_list = connectionsStore.remote_terminals.map(
        (term) => {
          const { id, alias, details1 } = term;
          let term_name = alias ? `(${alias})` : "";
          if (details1) {
            term_name += details1;
          }
          return {
            label: term_name,
            icon: "fas fa-terminal",
            onClick: () => {
              tabsStore.createTerminalTab(id, alias, details1)
            },
          };
        }
      );

      items.push({
        label: "SSH Consoles",
        icon: "fas fa-terminal",
        children: submenu_terminal_list,
      });
    }

    if (items.length > 0) {
      items.unshift({
        label: "Manage Connections",
        icon: "fas fa-gears",
        onClick: () => {
          Modal.getOrCreateInstance("#connections-modal").show()
        },
      });

      ContextMenu.showContextMenu({
        theme: "pgmanage",
        x: e.x,
        y: e.y,
        zIndex: 1000,
        minWidth: 230,
        items: items,
      });
    } else {
      startLoading();
      setTimeout(function () {
        tabsStore.createWorkspaceTab()
      }, 0);
    }
  }
}

export {
  refreshHeights,
  renameTab,
  checkBeforeChangeDatabase,
  showMenuNewTabOuter
};