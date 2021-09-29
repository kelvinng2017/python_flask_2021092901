Date.prototype.format = function (fmt) {
  var o = {
    "M+": this.getMonth() + 1,                   
    "d+": this.getDate(),                        
    "h+": this.getHours(),                       
    "m+": this.getMinutes(),                     
    "s+": this.getSeconds(),                     
    "q+": Math.floor((this.getMonth() + 3) / 3), 
    "S": this.getMilliseconds()                  
  };

  if (/(y+)/i.test(fmt)) {
    fmt = fmt.replace(RegExp.$1, (this.getFullYear() + "").substr(4 - RegExp.$1.length));
  }

  for (var k in o) {
    if (new RegExp("(" + k + ")", "i").test(fmt)) {
      fmt = fmt.replace(
        RegExp.$1, (RegExp.$1.length == 1) ? (o[k]) : (("00" + o[k]).substr(("" + o[k]).length)));
    }
  }
  return fmt;
}

function idRefresh() {
  let random = Math.floor(Math.random()*9000)+1000
  let date = new Date().format("YYYYMMDDHHMMSS")
  let commandid = date + random
  $('#strCOMMANDID').val(commandid)
}

$(document).ready(function(){
  $('#sidebar .sidebar-nav').find('li.active').removeClass('bg-gray-200 text-black-700');
  var sPath = window.location.pathname;
  $('#sidebar .sidebar-nav').find('a[href="' + sPath + '"]').addClass('bg-gray-200 text-black-700 fw-bolder');
});

// function setCookie(name, value, seconds){
//   seconds = seconds || 0
//   let expires =""
//   if( seconds != 0) {
//     let date = new Date();
//     date.setTime(date.getTime() + (seconds * 1000))
//     expires = "; expires=" + date.toGMTString()
//   }
//   document.cookie = name + "=" escape(value) + expires + "; path=/"
// }

// function setInfo(key, value) {
//   localStorage.setItem(key, value)
//   setCookie(key, value)
// }

// function getCookie(name) {
//   let nameEQ = name + "="
//   let ca = document.cookie.split(';')
//   for(let i = 0; i< ca.length; i++) {
//     let c = ca[i]
//     while (c.charAt(0) == '') {
//       c = c.substring(1, c.length)
//     }
//     if(c.indexOf(nameEQ) == 0) {
//       return unescape(c.substring(nameEQ.length, c.length))
//     }
//   }
//   return false
// }

// if(!getCookie('Token')){
//   localStorage.clear()
// }


