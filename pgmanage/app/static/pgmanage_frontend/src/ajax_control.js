/*
This file is part of OmniDB.
OmniDB is open-source software, distributed "AS IS" under the MIT license in the hope that it will be useful.

The MIT License (MIT)

Portions Copyright (c) 2015-2020, The OmniDB Team
Portions Copyright (c) 2017-2020, 2ndQuadrant Limited

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/

//Number of active AJAX calls
var v_calls_count = 0;
var v_is_loading = false;

/**
 * Used to add a loading gif modal above page content.
 */
function startLoading() {
	v_calls_count++;
	if (!v_is_loading) {

		$('#div_loading').fadeIn(100);
		v_is_loading = true;
	}
}

/**
 * Used to remove a loading gif modal above page content.
 */
function endLoading() {
	if(v_calls_count > 0) {
		v_calls_count--;
	}

	if(v_calls_count==0) {
		$('#div_loading').fadeOut(100);
		v_is_loading = false;
	}
}

/**
 * Used to get a cookie value from document, based on cookie name.
 * @param {string} name - the name of the cookie in the document.
 * @returns {string} cookie value, if exists.
 */

function getCookie(name) {
	var cookieValue = null;

	if(document.cookie && document.cookie !== '') {
		var cookies = document.cookie.split(';');

		for(var i = 0; i < cookies.length; i++) {
			var cookie = jQuery.trim(cookies[i]);

			// Does this cookie string begin with the name we want?
			if(cookie.substring(0, name.length + 1) === (name + '=')) {
				cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
				break;
			}
		}
	}

	return cookieValue;
}

/**
 * Used to get see if a http request is one of: GET, HEAD, OPTIONS, TRACE.
 * @param {string} method - the method to be checked.
 * @returns {boolean} if the http request is one of GET, HEAD, OPTIONS, TRACE or not.
 */
function csrfSafeMethod(method) {
	return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

export { startLoading, endLoading, getCookie, csrfSafeMethod}