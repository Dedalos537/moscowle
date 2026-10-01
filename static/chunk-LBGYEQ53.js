import{Aa as X,Ba as K,Ca as $t,Cc as re,Da as Ht,Dc as on,Ea as Ut,Ec as sn,Fa as Wt,Ga as Bt,Gb as Qt,Ha as Yt,Ia as Vt,Ja as W,Ka as Gt,Kb as en,Lb as tn,Pa as ne,Qa as Xt,R as N,Ra as Kt,Tb as nn,U as x,Ua as ae,Uc as ln,V as ge,Vc as fn,Wa as Jt,Wc as cn,X as te,Y as b,Z as j,aa as Lt,bb as Be,cb as ye,db as Zt,ia as k,ka as $e,mb as qt,qc as Ye,rc as an,sa as jt,ta as He,ua as zt,uc as be,va as ve,vc as I,xa as Ue,xc as rn,za as We}from"./chunk-TZD7SYSL.js";import{a as ee,b as ze}from"./chunk-DAQOROHW.js";var ie=class{_doc;constructor(a){this._doc=a}manager},Se=(()=>{class e extends ie{constructor(t){super(t)}supports(t){return!0}addEventListener(t,n,r,i){return t.addEventListener(n,r,i),()=>this.removeEventListener(t,n,r,i)}removeEventListener(t,n,r,i){return t.removeEventListener(n,r,i)}static \u0275fac=function(n){return new(n||e)(b(k))};static \u0275prov=x({token:e,factory:e.\u0275fac})}return e})(),Ee=new te(""),Ze=(()=>{class e{_zone;_plugins;_eventNameToPlugin=new Map;constructor(t,n){this._zone=n,t.forEach(o=>{o.manager=this});let r=t.filter(o=>!(o instanceof Se));this._plugins=r.slice().reverse();let i=t.find(o=>o instanceof Se);i&&this._plugins.push(i)}addEventListener(t,n,r,i){return this._findPluginFor(n).addEventListener(t,n,r,i)}getZone(){return this._zone}_findPluginFor(t){let n=this._eventNameToPlugin.get(t);if(n)return n;if(n=this._plugins.find(i=>i.supports(t)),!n)throw new N(5101,!1);return this._eventNameToPlugin.set(t,n),n}static \u0275fac=function(n){return new(n||e)(b(Ee),b(ae))};static \u0275prov=x({token:e,factory:e.\u0275fac})}return e})(),Ve="ng-app-id";function un(e){for(let a of e)a.remove()}function dn(e,a){let t=a.createElement("style");return t.textContent=e,t}function or(e,a,t,n){let r=e.head?.querySelectorAll(`style[${Ve}="${a}"],link[${Ve}="${a}"]`);if(r)for(let i of r)i.removeAttribute(Ve),i instanceof HTMLLinkElement?n.set(i.href.slice(i.href.lastIndexOf("/")+1),{usage:0,elements:[i]}):i.textContent&&t.set(i.textContent,{usage:0,elements:[i]})}function Xe(e,a){let t=a.createElement("link");return t.setAttribute("rel","stylesheet"),t.setAttribute("href",e),t}var qe=(()=>{class e{doc;appId;nonce;inline=new Map;external=new Map;hosts=new Set;constructor(t,n,r,i={}){this.doc=t,this.appId=n,this.nonce=r,or(t,n,this.inline,this.external),this.hosts.add(t.head)}addStyles(t,n){for(let r of t)this.addUsage(r,this.inline,dn);n?.forEach(r=>this.addUsage(r,this.external,Xe))}removeStyles(t,n){for(let r of t)this.removeUsage(r,this.inline);n?.forEach(r=>this.removeUsage(r,this.external))}addUsage(t,n,r){let i=n.get(t);i?i.usage++:n.set(t,{usage:1,elements:[...this.hosts].map(o=>this.addElement(o,r(t,this.doc)))})}removeUsage(t,n){let r=n.get(t);r&&(r.usage--,r.usage<=0&&(un(r.elements),n.delete(t)))}ngOnDestroy(){for(let[,{elements:t}]of[...this.inline,...this.external])un(t);this.hosts.clear()}addHost(t){this.hosts.add(t);for(let[n,{elements:r}]of this.inline)r.push(this.addElement(t,dn(n,this.doc)));for(let[n,{elements:r}]of this.external)r.push(this.addElement(t,Xe(n,this.doc)))}removeHost(t){this.hosts.delete(t)}addElement(t,n){return this.nonce&&n.setAttribute("nonce",this.nonce),t.appendChild(n)}static \u0275fac=function(n){return new(n||e)(b(k),b(He),b(Ue,8),b(ve))};static \u0275prov=x({token:e,factory:e.\u0275fac})}return e})(),Ge={svg:"http://www.w3.org/2000/svg",xhtml:"http://www.w3.org/1999/xhtml",xlink:"http://www.w3.org/1999/xlink",xml:"http://www.w3.org/XML/1998/namespace",xmlns:"http://www.w3.org/2000/xmlns/",math:"http://www.w3.org/1998/Math/MathML"},Qe=/%COMP%/g;var pn="%COMP%",sr=`_nghost-${pn}`,lr=`_ngcontent-${pn}`,fr=!0,cr=new te("",{providedIn:"root",factory:()=>fr});function ur(e){return lr.replace(Qe,e)}function dr(e){return sr.replace(Qe,e)}function hn(e,a){return a.map(t=>t.replace(Qe,e))}var et=(()=>{class e{eventManager;sharedStylesHost;appId;removeStylesOnCompDestroy;doc;ngZone;nonce;tracingService;rendererByCompId=new Map;defaultRenderer;platformIsServer;constructor(t,n,r,i,o,s,l=null,c=null){this.eventManager=t,this.sharedStylesHost=n,this.appId=r,this.removeStylesOnCompDestroy=i,this.doc=o,this.ngZone=s,this.nonce=l,this.tracingService=c,this.platformIsServer=!1,this.defaultRenderer=new oe(t,o,s,this.platformIsServer,this.tracingService)}createRenderer(t,n){if(!t||!n)return this.defaultRenderer;let r=this.getOrCreateRenderer(t,n);return r instanceof we?r.applyToHost(t):r instanceof se&&r.applyStyles(),r}getOrCreateRenderer(t,n){let r=this.rendererByCompId,i=r.get(n.id);if(!i){let o=this.doc,s=this.ngZone,l=this.eventManager,c=this.sharedStylesHost,u=this.removeStylesOnCompDestroy,d=this.platformIsServer,g=this.tracingService;switch(n.encapsulation){case We.Emulated:i=new we(l,c,n,this.appId,u,o,s,d,g);break;case We.ShadowDom:return new Ke(l,c,t,n,o,s,this.nonce,d,g);default:i=new se(l,c,n,u,o,s,d,g);break}r.set(n.id,i)}return i}ngOnDestroy(){this.rendererByCompId.clear()}componentReplaced(t){this.rendererByCompId.delete(t)}static \u0275fac=function(n){return new(n||e)(b(Ze),b(qe),b(He),b(cr),b(k),b(ae),b(Ue),b(Kt,8))};static \u0275prov=x({token:e,factory:e.\u0275fac})}return e})(),oe=class{eventManager;doc;ngZone;platformIsServer;tracingService;data=Object.create(null);throwOnSyntheticProps=!0;constructor(a,t,n,r,i){this.eventManager=a,this.doc=t,this.ngZone=n,this.platformIsServer=r,this.tracingService=i}destroy(){}destroyNode=null;createElement(a,t){return t?this.doc.createElementNS(Ge[t]||t,a):this.doc.createElement(a)}createComment(a){return this.doc.createComment(a)}createText(a){return this.doc.createTextNode(a)}appendChild(a,t){(mn(a)?a.content:a).appendChild(t)}insertBefore(a,t,n){a&&(mn(a)?a.content:a).insertBefore(t,n)}removeChild(a,t){t.remove()}selectRootElement(a,t){let n=typeof a=="string"?this.doc.querySelector(a):a;if(!n)throw new N(-5104,!1);return t||(n.textContent=""),n}parentNode(a){return a.parentNode}nextSibling(a){return a.nextSibling}setAttribute(a,t,n,r){if(r){t=r+":"+t;let i=Ge[r];i?a.setAttributeNS(i,t,n):a.setAttribute(t,n)}else a.setAttribute(t,n)}removeAttribute(a,t,n){if(n){let r=Ge[n];r?a.removeAttributeNS(r,t):a.removeAttribute(`${n}:${t}`)}else a.removeAttribute(t)}addClass(a,t){a.classList.add(t)}removeClass(a,t){a.classList.remove(t)}setStyle(a,t,n,r){r&(ne.DashCase|ne.Important)?a.style.setProperty(t,n,r&ne.Important?"important":""):a.style[t]=n}removeStyle(a,t,n){n&ne.DashCase?a.style.removeProperty(t):a.style[t]=""}setProperty(a,t,n){a!=null&&(a[t]=n)}setValue(a,t){a.nodeValue=t}listen(a,t,n,r){if(typeof a=="string"&&(a=re().getGlobalEventTarget(this.doc,a),!a))throw new N(5102,!1);let i=this.decoratePreventDefault(n);return this.tracingService?.wrapEventListener&&(i=this.tracingService.wrapEventListener(a,t,i)),this.eventManager.addEventListener(a,t,i,r)}decoratePreventDefault(a){return t=>{if(t==="__ngUnwrap__")return a;a(t)===!1&&t.preventDefault()}}};function mn(e){return e.tagName==="TEMPLATE"&&e.content!==void 0}var Ke=class extends oe{sharedStylesHost;hostEl;shadowRoot;constructor(a,t,n,r,i,o,s,l,c){super(a,i,o,l,c),this.sharedStylesHost=t,this.hostEl=n,this.shadowRoot=n.attachShadow({mode:"open"}),this.sharedStylesHost.addHost(this.shadowRoot);let u=r.styles;u=hn(r.id,u);for(let g of u){let p=document.createElement("style");s&&p.setAttribute("nonce",s),p.textContent=g,this.shadowRoot.appendChild(p)}let d=r.getExternalStyles?.();if(d)for(let g of d){let p=Xe(g,i);s&&p.setAttribute("nonce",s),this.shadowRoot.appendChild(p)}}nodeOrShadowRoot(a){return a===this.hostEl?this.shadowRoot:a}appendChild(a,t){return super.appendChild(this.nodeOrShadowRoot(a),t)}insertBefore(a,t,n){return super.insertBefore(this.nodeOrShadowRoot(a),t,n)}removeChild(a,t){return super.removeChild(null,t)}parentNode(a){return this.nodeOrShadowRoot(super.parentNode(this.nodeOrShadowRoot(a)))}destroy(){this.sharedStylesHost.removeHost(this.shadowRoot)}},se=class extends oe{sharedStylesHost;removeStylesOnCompDestroy;styles;styleUrls;constructor(a,t,n,r,i,o,s,l,c){super(a,i,o,s,l),this.sharedStylesHost=t,this.removeStylesOnCompDestroy=r;let u=n.styles;this.styles=c?hn(c,u):u,this.styleUrls=n.getExternalStyles?.(c)}applyStyles(){this.sharedStylesHost.addStyles(this.styles,this.styleUrls)}destroy(){this.removeStylesOnCompDestroy&&Xt.size===0&&this.sharedStylesHost.removeStyles(this.styles,this.styleUrls)}},we=class extends se{contentAttr;hostAttr;constructor(a,t,n,r,i,o,s,l,c){let u=r+"-"+n.id;super(a,t,n,i,o,s,l,c,u),this.contentAttr=ur(u),this.hostAttr=dr(u)}applyToHost(a){this.applyStyles(),this.setAttribute(a,this.hostAttr,"")}createElement(a,t){let n=super.createElement(a,t);return super.setAttribute(n,this.contentAttr,""),n}};var Ae=class e extends sn{supportsDOMEvents=!0;static makeCurrent(){on(new e)}onAndCancel(a,t,n,r){return a.addEventListener(t,n,r),()=>{a.removeEventListener(t,n,r)}}dispatchEvent(a,t){a.dispatchEvent(t)}remove(a){a.remove()}createElement(a,t){return t=t||this.getDefaultDocument(),t.createElement(a)}createHtmlDocument(){return document.implementation.createHTMLDocument("fakeTitle")}getDefaultDocument(){return document}isElementNode(a){return a.nodeType===Node.ELEMENT_NODE}isShadowRoot(a){return a instanceof DocumentFragment}getGlobalEventTarget(a,t){return t==="window"?window:t==="document"?a:t==="body"?a.body:null}getBaseHref(a){let t=pr();return t==null?null:hr(t)}resetBaseElement(){le=null}getUserAgent(){return window.navigator.userAgent}getCookie(a){return ln(document.cookie,a)}},le=null;function pr(){return le=le||document.head.querySelector("base"),le?le.getAttribute("href"):null}function hr(e){return new URL(e,document.baseURI).pathname}var gr=(()=>{class e{build(){return new XMLHttpRequest}static \u0275fac=function(n){return new(n||e)};static \u0275prov=x({token:e,factory:e.\u0275fac})}return e})(),gn=["alt","control","meta","shift"],vr={"\b":"Backspace","	":"Tab","\x7F":"Delete","\x1B":"Escape",Del:"Delete",Esc:"Escape",Left:"ArrowLeft",Right:"ArrowRight",Up:"ArrowUp",Down:"ArrowDown",Menu:"ContextMenu",Scroll:"ScrollLock",Win:"OS"},yr={alt:e=>e.altKey,control:e=>e.ctrlKey,meta:e=>e.metaKey,shift:e=>e.shiftKey},vn=(()=>{class e extends ie{constructor(t){super(t)}supports(t){return e.parseEventName(t)!=null}addEventListener(t,n,r,i){let o=e.parseEventName(n),s=e.eventCallback(o.fullKey,r,this.manager.getZone());return this.manager.getZone().runOutsideAngular(()=>re().onAndCancel(t,o.domEventName,s,i))}static parseEventName(t){let n=t.toLowerCase().split("."),r=n.shift();if(n.length===0||!(r==="keydown"||r==="keyup"))return null;let i=e._normalizeKey(n.pop()),o="",s=n.indexOf("code");if(s>-1&&(n.splice(s,1),o="code."),gn.forEach(c=>{let u=n.indexOf(c);u>-1&&(n.splice(u,1),o+=c+".")}),o+=i,n.length!=0||i.length===0)return null;let l={};return l.domEventName=r,l.fullKey=o,l}static matchEventFullKeyCode(t,n){let r=vr[t.key]||t.key,i="";return n.indexOf("code.")>-1&&(r=t.code,i="code."),r==null||!r?!1:(r=r.toLowerCase(),r===" "?r="space":r==="."&&(r="dot"),gn.forEach(o=>{if(o!==r){let s=yr[o];s(t)&&(i+=o+".")}}),i+=r,i===n)}static eventCallback(t,n,r){return i=>{e.matchEventFullKeyCode(i,t)&&r.runGuarded(()=>n(i))}}static _normalizeKey(t){return t==="esc"?"escape":t}static \u0275fac=function(n){return new(n||e)(b(k))};static \u0275prov=x({token:e,factory:e.\u0275fac})}return e})();function br(e,a,t){let n=ee({rootComponent:e,platformRef:t?.platformRef},Sr(a));return rn(n)}function Sr(e){return{appProviders:[...Ir,...e?.providers??[]],platformProviders:xr}}function wr(){Ae.makeCurrent()}function Er(){return new $e}function Ar(){return jt(document),document}var xr=[{provide:ve,useValue:cn},{provide:zt,useValue:wr,multi:!0},{provide:k,useFactory:Ar}];var Ir=[{provide:Lt,useValue:"root"},{provide:$e,useFactory:Er},{provide:Ee,useClass:Se,multi:!0,deps:[k]},{provide:Ee,useClass:vn,multi:!0,deps:[k]},et,qe,Ze,{provide:Jt,useExisting:et},{provide:fn,useClass:gr},[]];var ef=(()=>{class e{_doc;constructor(t){this._doc=t}getTitle(){return this._doc.title}setTitle(t){this._doc.title=t||""}static \u0275fac=function(n){return new(n||e)(b(k))};static \u0275prov=x({token:e,factory:e.\u0275fac,providedIn:"root"})}return e})();var tt=(()=>{class e{static \u0275fac=function(n){return new(n||e)};static \u0275prov=x({token:e,factory:function(n){let r=null;return n?r=new(n||e):r=b(kr),r},providedIn:"root"})}return e})(),kr=(()=>{class e extends tt{_doc;constructor(t){super(),this._doc=t}sanitize(t,n){if(n==null)return null;switch(t){case W.NONE:return n;case W.HTML:return K(n,"HTML")?X(n):Vt(this._doc,String(n)).toString();case W.STYLE:return K(n,"Style")?X(n):n;case W.SCRIPT:if(K(n,"Script"))return X(n);throw new N(5200,!1);case W.URL:return K(n,"URL")?X(n):Yt(String(n));case W.RESOURCE_URL:if(K(n,"ResourceURL"))return X(n);throw new N(5201,!1);default:throw new N(5202,!1)}}bypassSecurityTrustHtml(t){return $t(t)}bypassSecurityTrustStyle(t){return Ht(t)}bypassSecurityTrustScript(t){return Ut(t)}bypassSecurityTrustUrl(t){return Wt(t)}bypassSecurityTrustResourceUrl(t){return Bt(t)}static \u0275fac=function(n){return new(n||e)(b(k))};static \u0275prov=x({token:e,factory:e.\u0275fac,providedIn:"root"})}return e})();function ft(e,a){(a==null||a>e.length)&&(a=e.length);for(var t=0,n=Array(a);t<a;t++)n[t]=e[t];return n}function Tr(e){if(Array.isArray(e))return e}function Mr(e){if(Array.isArray(e))return ft(e)}function _r(e,a){if(!(e instanceof a))throw new TypeError("Cannot call a class as a function")}function yn(e,a){for(var t=0;t<a.length;t++){var n=a[t];n.enumerable=n.enumerable||!1,n.configurable=!0,"value"in n&&(n.writable=!0),Object.defineProperty(e,Jn(n.key),n)}}function Or(e,a,t){return a&&yn(e.prototype,a),t&&yn(e,t),Object.defineProperty(e,"prototype",{writable:!1}),e}function Ce(e,a){var t=typeof Symbol<"u"&&e[Symbol.iterator]||e["@@iterator"];if(!t){if(Array.isArray(e)||(t=xt(e))||a&&e&&typeof e.length=="number"){t&&(e=t);var n=0,r=function(){};return{s:r,n:function(){return n>=e.length?{done:!0}:{done:!1,value:e[n++]}},e:function(l){throw l},f:r}}throw new TypeError(`Invalid attempt to iterate non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}var i,o=!0,s=!1;return{s:function(){t=t.call(e)},n:function(){var l=t.next();return o=l.done,l},e:function(l){s=!0,i=l},f:function(){try{o||t.return==null||t.return()}finally{if(s)throw i}}}}function h(e,a,t){return(a=Jn(a))in e?Object.defineProperty(e,a,{value:t,enumerable:!0,configurable:!0,writable:!0}):e[a]=t,e}function Dr(e){if(typeof Symbol<"u"&&e[Symbol.iterator]!=null||e["@@iterator"]!=null)return Array.from(e)}function Pr(e,a){var t=e==null?null:typeof Symbol<"u"&&e[Symbol.iterator]||e["@@iterator"];if(t!=null){var n,r,i,o,s=[],l=!0,c=!1;try{if(i=(t=t.call(e)).next,a===0){if(Object(t)!==t)return;l=!1}else for(;!(l=(n=i.call(t)).done)&&(s.push(n.value),s.length!==a);l=!0);}catch(u){c=!0,r=u}finally{try{if(!l&&t.return!=null&&(o=t.return(),Object(o)!==o))return}finally{if(c)throw r}}return s}}function Nr(){throw new TypeError(`Invalid attempt to destructure non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}function Rr(){throw new TypeError(`Invalid attempt to spread non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}function bn(e,a){var t=Object.keys(e);if(Object.getOwnPropertySymbols){var n=Object.getOwnPropertySymbols(e);a&&(n=n.filter(function(r){return Object.getOwnPropertyDescriptor(e,r).enumerable})),t.push.apply(t,n)}return t}function f(e){for(var a=1;a<arguments.length;a++){var t=arguments[a]!=null?arguments[a]:{};a%2?bn(Object(t),!0).forEach(function(n){h(e,n,t[n])}):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(t)):bn(Object(t)).forEach(function(n){Object.defineProperty(e,n,Object.getOwnPropertyDescriptor(t,n))})}return e}function De(e,a){return Tr(e)||Pr(e,a)||xt(e,a)||Nr()}function O(e){return Mr(e)||Dr(e)||xt(e)||Rr()}function Fr(e,a){if(typeof e!="object"||!e)return e;var t=e[Symbol.toPrimitive];if(t!==void 0){var n=t.call(e,a||"default");if(typeof n!="object")return n;throw new TypeError("@@toPrimitive must return a primitive value.")}return(a==="string"?String:Number)(e)}function Jn(e){var a=Fr(e,"string");return typeof a=="symbol"?a:a+""}function Me(e){"@babel/helpers - typeof";return Me=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(a){return typeof a}:function(a){return a&&typeof Symbol=="function"&&a.constructor===Symbol&&a!==Symbol.prototype?"symbol":typeof a},Me(e)}function xt(e,a){if(e){if(typeof e=="string")return ft(e,a);var t={}.toString.call(e).slice(8,-1);return t==="Object"&&e.constructor&&(t=e.constructor.name),t==="Map"||t==="Set"?Array.from(e):t==="Arguments"||/^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t)?ft(e,a):void 0}}var Sn=function(){},It={},Zn={},qn=null,Qn={mark:Sn,measure:Sn};try{typeof window<"u"&&(It=window),typeof document<"u"&&(Zn=document),typeof MutationObserver<"u"&&(qn=MutationObserver),typeof performance<"u"&&(Qn=performance)}catch{}var Lr=It.navigator||{},wn=Lr.userAgent,En=wn===void 0?"":wn,$=It,v=Zn,An=qn,xe=Qn,af=!!$.document,L=!!v.documentElement&&!!v.head&&typeof v.addEventListener=="function"&&typeof v.createElement=="function",ea=~En.indexOf("MSIE")||~En.indexOf("Trident/"),nt,jr=/fa(k|kd|s|r|l|t|d|dr|dl|dt|b|slr|slpr|wsb|tl|ns|nds|es|gt|jr|jfr|jdr|usb|ufsb|udsb|cr|ss|sr|sl|st|sds|sdr|sdl|sdt)?[\-\ ]/,zr=/Font ?Awesome ?([567 ]*)(Solid|Regular|Light|Thin|Duotone|Brands|Free|Pro|Sharp Duotone|Sharp|Kit|Notdog Duo|Notdog|Chisel|Etch|Graphite|Thumbprint|Jelly Fill|Jelly Duo|Jelly|Utility|Utility Fill|Utility Duo|Slab Press|Slab|Whiteboard)?.*/i,ta={classic:{fa:"solid",fas:"solid","fa-solid":"solid",far:"regular","fa-regular":"regular",fal:"light","fa-light":"light",fat:"thin","fa-thin":"thin",fab:"brands","fa-brands":"brands"},duotone:{fa:"solid",fad:"solid","fa-solid":"solid","fa-duotone":"solid",fadr:"regular","fa-regular":"regular",fadl:"light","fa-light":"light",fadt:"thin","fa-thin":"thin"},sharp:{fa:"solid",fass:"solid","fa-solid":"solid",fasr:"regular","fa-regular":"regular",fasl:"light","fa-light":"light",fast:"thin","fa-thin":"thin"},"sharp-duotone":{fa:"solid",fasds:"solid","fa-solid":"solid",fasdr:"regular","fa-regular":"regular",fasdl:"light","fa-light":"light",fasdt:"thin","fa-thin":"thin"},slab:{"fa-regular":"regular",faslr:"regular"},"slab-press":{"fa-regular":"regular",faslpr:"regular"},thumbprint:{"fa-light":"light",fatl:"light"},whiteboard:{"fa-semibold":"semibold",fawsb:"semibold"},notdog:{"fa-solid":"solid",fans:"solid"},"notdog-duo":{"fa-solid":"solid",fands:"solid"},etch:{"fa-solid":"solid",faes:"solid"},graphite:{"fa-thin":"thin",fagt:"thin"},jelly:{"fa-regular":"regular",fajr:"regular"},"jelly-fill":{"fa-regular":"regular",fajfr:"regular"},"jelly-duo":{"fa-regular":"regular",fajdr:"regular"},chisel:{"fa-regular":"regular",facr:"regular"},utility:{"fa-semibold":"semibold",fausb:"semibold"},"utility-duo":{"fa-semibold":"semibold",faudsb:"semibold"},"utility-fill":{"fa-semibold":"semibold",faufsb:"semibold"}},$r={GROUP:"duotone-group",SWAP_OPACITY:"swap-opacity",PRIMARY:"primary",SECONDARY:"secondary"},na=["fa-classic","fa-duotone","fa-sharp","fa-sharp-duotone","fa-thumbprint","fa-whiteboard","fa-notdog","fa-notdog-duo","fa-chisel","fa-etch","fa-graphite","fa-jelly","fa-jelly-fill","fa-jelly-duo","fa-slab","fa-slab-press","fa-utility","fa-utility-duo","fa-utility-fill"],E="classic",me="duotone",aa="sharp",ra="sharp-duotone",ia="chisel",oa="etch",sa="graphite",la="jelly",fa="jelly-duo",ca="jelly-fill",ua="notdog",da="notdog-duo",ma="slab",pa="slab-press",ha="thumbprint",ga="utility",va="utility-duo",ya="utility-fill",ba="whiteboard",Hr="Classic",Ur="Duotone",Wr="Sharp",Br="Sharp Duotone",Yr="Chisel",Vr="Etch",Gr="Graphite",Xr="Jelly",Kr="Jelly Duo",Jr="Jelly Fill",Zr="Notdog",qr="Notdog Duo",Qr="Slab",ei="Slab Press",ti="Thumbprint",ni="Utility",ai="Utility Duo",ri="Utility Fill",ii="Whiteboard",Sa=[E,me,aa,ra,ia,oa,sa,la,fa,ca,ua,da,ma,pa,ha,ga,va,ya,ba],rf=(nt={},h(h(h(h(h(h(h(h(h(h(nt,E,Hr),me,Ur),aa,Wr),ra,Br),ia,Yr),oa,Vr),sa,Gr),la,Xr),fa,Kr),ca,Jr),h(h(h(h(h(h(h(h(h(nt,ua,Zr),da,qr),ma,Qr),pa,ei),ha,ti),ga,ni),va,ai),ya,ri),ba,ii)),oi={classic:{900:"fas",400:"far",normal:"far",300:"fal",100:"fat"},duotone:{900:"fad",400:"fadr",300:"fadl",100:"fadt"},sharp:{900:"fass",400:"fasr",300:"fasl",100:"fast"},"sharp-duotone":{900:"fasds",400:"fasdr",300:"fasdl",100:"fasdt"},slab:{400:"faslr"},"slab-press":{400:"faslpr"},whiteboard:{600:"fawsb"},thumbprint:{300:"fatl"},notdog:{900:"fans"},"notdog-duo":{900:"fands"},etch:{900:"faes"},graphite:{100:"fagt"},chisel:{400:"facr"},jelly:{400:"fajr"},"jelly-fill":{400:"fajfr"},"jelly-duo":{400:"fajdr"},utility:{600:"fausb"},"utility-duo":{600:"faudsb"},"utility-fill":{600:"faufsb"}},si={"Font Awesome 7 Free":{900:"fas",400:"far"},"Font Awesome 7 Pro":{900:"fas",400:"far",normal:"far",300:"fal",100:"fat"},"Font Awesome 7 Brands":{400:"fab",normal:"fab"},"Font Awesome 7 Duotone":{900:"fad",400:"fadr",normal:"fadr",300:"fadl",100:"fadt"},"Font Awesome 7 Sharp":{900:"fass",400:"fasr",normal:"fasr",300:"fasl",100:"fast"},"Font Awesome 7 Sharp Duotone":{900:"fasds",400:"fasdr",normal:"fasdr",300:"fasdl",100:"fasdt"},"Font Awesome 7 Jelly":{400:"fajr",normal:"fajr"},"Font Awesome 7 Jelly Fill":{400:"fajfr",normal:"fajfr"},"Font Awesome 7 Jelly Duo":{400:"fajdr",normal:"fajdr"},"Font Awesome 7 Slab":{400:"faslr",normal:"faslr"},"Font Awesome 7 Slab Press":{400:"faslpr",normal:"faslpr"},"Font Awesome 7 Thumbprint":{300:"fatl",normal:"fatl"},"Font Awesome 7 Notdog":{900:"fans",normal:"fans"},"Font Awesome 7 Notdog Duo":{900:"fands",normal:"fands"},"Font Awesome 7 Etch":{900:"faes",normal:"faes"},"Font Awesome 7 Graphite":{100:"fagt",normal:"fagt"},"Font Awesome 7 Chisel":{400:"facr",normal:"facr"},"Font Awesome 7 Whiteboard":{600:"fawsb",normal:"fawsb"},"Font Awesome 7 Utility":{600:"fausb",normal:"fausb"},"Font Awesome 7 Utility Duo":{600:"faudsb",normal:"faudsb"},"Font Awesome 7 Utility Fill":{600:"faufsb",normal:"faufsb"}},li=new Map([["classic",{defaultShortPrefixId:"fas",defaultStyleId:"solid",styleIds:["solid","regular","light","thin","brands"],futureStyleIds:[],defaultFontWeight:900}],["duotone",{defaultShortPrefixId:"fad",defaultStyleId:"solid",styleIds:["solid","regular","light","thin"],futureStyleIds:[],defaultFontWeight:900}],["sharp",{defaultShortPrefixId:"fass",defaultStyleId:"solid",styleIds:["solid","regular","light","thin"],futureStyleIds:[],defaultFontWeight:900}],["sharp-duotone",{defaultShortPrefixId:"fasds",defaultStyleId:"solid",styleIds:["solid","regular","light","thin"],futureStyleIds:[],defaultFontWeight:900}],["chisel",{defaultShortPrefixId:"facr",defaultStyleId:"regular",styleIds:["regular"],futureStyleIds:[],defaultFontWeight:400}],["etch",{defaultShortPrefixId:"faes",defaultStyleId:"solid",styleIds:["solid"],futureStyleIds:[],defaultFontWeight:900}],["graphite",{defaultShortPrefixId:"fagt",defaultStyleId:"thin",styleIds:["thin"],futureStyleIds:[],defaultFontWeight:100}],["jelly",{defaultShortPrefixId:"fajr",defaultStyleId:"regular",styleIds:["regular"],futureStyleIds:[],defaultFontWeight:400}],["jelly-duo",{defaultShortPrefixId:"fajdr",defaultStyleId:"regular",styleIds:["regular"],futureStyleIds:[],defaultFontWeight:400}],["jelly-fill",{defaultShortPrefixId:"fajfr",defaultStyleId:"regular",styleIds:["regular"],futureStyleIds:[],defaultFontWeight:400}],["notdog",{defaultShortPrefixId:"fans",defaultStyleId:"solid",styleIds:["solid"],futureStyleIds:[],defaultFontWeight:900}],["notdog-duo",{defaultShortPrefixId:"fands",defaultStyleId:"solid",styleIds:["solid"],futureStyleIds:[],defaultFontWeight:900}],["slab",{defaultShortPrefixId:"faslr",defaultStyleId:"regular",styleIds:["regular"],futureStyleIds:[],defaultFontWeight:400}],["slab-press",{defaultShortPrefixId:"faslpr",defaultStyleId:"regular",styleIds:["regular"],futureStyleIds:[],defaultFontWeight:400}],["thumbprint",{defaultShortPrefixId:"fatl",defaultStyleId:"light",styleIds:["light"],futureStyleIds:[],defaultFontWeight:300}],["utility",{defaultShortPrefixId:"fausb",defaultStyleId:"semibold",styleIds:["semibold"],futureStyleIds:[],defaultFontWeight:600}],["utility-duo",{defaultShortPrefixId:"faudsb",defaultStyleId:"semibold",styleIds:["semibold"],futureStyleIds:[],defaultFontWeight:600}],["utility-fill",{defaultShortPrefixId:"faufsb",defaultStyleId:"semibold",styleIds:["semibold"],futureStyleIds:[],defaultFontWeight:600}],["whiteboard",{defaultShortPrefixId:"fawsb",defaultStyleId:"semibold",styleIds:["semibold"],futureStyleIds:[],defaultFontWeight:600}]]),fi={chisel:{regular:"facr"},classic:{brands:"fab",light:"fal",regular:"far",solid:"fas",thin:"fat"},duotone:{light:"fadl",regular:"fadr",solid:"fad",thin:"fadt"},etch:{solid:"faes"},graphite:{thin:"fagt"},jelly:{regular:"fajr"},"jelly-duo":{regular:"fajdr"},"jelly-fill":{regular:"fajfr"},notdog:{solid:"fans"},"notdog-duo":{solid:"fands"},sharp:{light:"fasl",regular:"fasr",solid:"fass",thin:"fast"},"sharp-duotone":{light:"fasdl",regular:"fasdr",solid:"fasds",thin:"fasdt"},slab:{regular:"faslr"},"slab-press":{regular:"faslpr"},thumbprint:{light:"fatl"},utility:{semibold:"fausb"},"utility-duo":{semibold:"faudsb"},"utility-fill":{semibold:"faufsb"},whiteboard:{semibold:"fawsb"}},wa=["fak","fa-kit","fakd","fa-kit-duotone"],xn={kit:{fak:"kit","fa-kit":"kit"},"kit-duotone":{fakd:"kit-duotone","fa-kit-duotone":"kit-duotone"}},ci=["kit"],ui="kit",di="kit-duotone",mi="Kit",pi="Kit Duotone",of=h(h({},ui,mi),di,pi),hi={kit:{"fa-kit":"fak"},"kit-duotone":{"fa-kit-duotone":"fakd"}},gi={"Font Awesome Kit":{400:"fak",normal:"fak"},"Font Awesome Kit Duotone":{400:"fakd",normal:"fakd"}},vi={kit:{fak:"fa-kit"},"kit-duotone":{fakd:"fa-kit-duotone"}},In={kit:{kit:"fak"},"kit-duotone":{"kit-duotone":"fakd"}},at,Ie={GROUP:"duotone-group",SWAP_OPACITY:"swap-opacity",PRIMARY:"primary",SECONDARY:"secondary"},yi=["fa-classic","fa-duotone","fa-sharp","fa-sharp-duotone","fa-thumbprint","fa-whiteboard","fa-notdog","fa-notdog-duo","fa-chisel","fa-etch","fa-graphite","fa-jelly","fa-jelly-fill","fa-jelly-duo","fa-slab","fa-slab-press","fa-utility","fa-utility-duo","fa-utility-fill"],bi="classic",Si="duotone",wi="sharp",Ei="sharp-duotone",Ai="chisel",xi="etch",Ii="graphite",Ci="jelly",ki="jelly-duo",Ti="jelly-fill",Mi="notdog",_i="notdog-duo",Oi="slab",Di="slab-press",Pi="thumbprint",Ni="utility",Ri="utility-duo",Fi="utility-fill",Li="whiteboard",ji="Classic",zi="Duotone",$i="Sharp",Hi="Sharp Duotone",Ui="Chisel",Wi="Etch",Bi="Graphite",Yi="Jelly",Vi="Jelly Duo",Gi="Jelly Fill",Xi="Notdog",Ki="Notdog Duo",Ji="Slab",Zi="Slab Press",qi="Thumbprint",Qi="Utility",eo="Utility Duo",to="Utility Fill",no="Whiteboard",sf=(at={},h(h(h(h(h(h(h(h(h(h(at,bi,ji),Si,zi),wi,$i),Ei,Hi),Ai,Ui),xi,Wi),Ii,Bi),Ci,Yi),ki,Vi),Ti,Gi),h(h(h(h(h(h(h(h(h(at,Mi,Xi),_i,Ki),Oi,Ji),Di,Zi),Pi,qi),Ni,Qi),Ri,eo),Fi,to),Li,no)),ao="kit",ro="kit-duotone",io="Kit",oo="Kit Duotone",lf=h(h({},ao,io),ro,oo),so={classic:{"fa-brands":"fab","fa-duotone":"fad","fa-light":"fal","fa-regular":"far","fa-solid":"fas","fa-thin":"fat"},duotone:{"fa-regular":"fadr","fa-light":"fadl","fa-thin":"fadt"},sharp:{"fa-solid":"fass","fa-regular":"fasr","fa-light":"fasl","fa-thin":"fast"},"sharp-duotone":{"fa-solid":"fasds","fa-regular":"fasdr","fa-light":"fasdl","fa-thin":"fasdt"},slab:{"fa-regular":"faslr"},"slab-press":{"fa-regular":"faslpr"},whiteboard:{"fa-semibold":"fawsb"},thumbprint:{"fa-light":"fatl"},notdog:{"fa-solid":"fans"},"notdog-duo":{"fa-solid":"fands"},etch:{"fa-solid":"faes"},graphite:{"fa-thin":"fagt"},jelly:{"fa-regular":"fajr"},"jelly-fill":{"fa-regular":"fajfr"},"jelly-duo":{"fa-regular":"fajdr"},chisel:{"fa-regular":"facr"},utility:{"fa-semibold":"fausb"},"utility-duo":{"fa-semibold":"faudsb"},"utility-fill":{"fa-semibold":"faufsb"}},lo={classic:["fas","far","fal","fat","fad"],duotone:["fadr","fadl","fadt"],sharp:["fass","fasr","fasl","fast"],"sharp-duotone":["fasds","fasdr","fasdl","fasdt"],slab:["faslr"],"slab-press":["faslpr"],whiteboard:["fawsb"],thumbprint:["fatl"],notdog:["fans"],"notdog-duo":["fands"],etch:["faes"],graphite:["fagt"],jelly:["fajr"],"jelly-fill":["fajfr"],"jelly-duo":["fajdr"],chisel:["facr"],utility:["fausb"],"utility-duo":["faudsb"],"utility-fill":["faufsb"]},ct={classic:{fab:"fa-brands",fad:"fa-duotone",fal:"fa-light",far:"fa-regular",fas:"fa-solid",fat:"fa-thin"},duotone:{fadr:"fa-regular",fadl:"fa-light",fadt:"fa-thin"},sharp:{fass:"fa-solid",fasr:"fa-regular",fasl:"fa-light",fast:"fa-thin"},"sharp-duotone":{fasds:"fa-solid",fasdr:"fa-regular",fasdl:"fa-light",fasdt:"fa-thin"},slab:{faslr:"fa-regular"},"slab-press":{faslpr:"fa-regular"},whiteboard:{fawsb:"fa-semibold"},thumbprint:{fatl:"fa-light"},notdog:{fans:"fa-solid"},"notdog-duo":{fands:"fa-solid"},etch:{faes:"fa-solid"},graphite:{fagt:"fa-thin"},jelly:{fajr:"fa-regular"},"jelly-fill":{fajfr:"fa-regular"},"jelly-duo":{fajdr:"fa-regular"},chisel:{facr:"fa-regular"},utility:{fausb:"fa-semibold"},"utility-duo":{faudsb:"fa-semibold"},"utility-fill":{faufsb:"fa-semibold"}},fo=["fa-solid","fa-regular","fa-light","fa-thin","fa-duotone","fa-brands","fa-semibold"],Ea=["fa","fas","far","fal","fat","fad","fadr","fadl","fadt","fab","fass","fasr","fasl","fast","fasds","fasdr","fasdl","fasdt","faslr","faslpr","fawsb","fatl","fans","fands","faes","fagt","fajr","fajfr","fajdr","facr","fausb","faudsb","faufsb"].concat(yi,fo),co=["solid","regular","light","thin","duotone","brands","semibold"],Aa=[1,2,3,4,5,6,7,8,9,10],uo=Aa.concat([11,12,13,14,15,16,17,18,19,20]),mo=["aw","fw","pull-left","pull-right"],po=[].concat(O(Object.keys(lo)),co,mo,["2xs","xs","sm","lg","xl","2xl","beat","border","fade","beat-fade","bounce","flip-both","flip-horizontal","flip-vertical","flip","inverse","layers","layers-bottom-left","layers-bottom-right","layers-counter","layers-text","layers-top-left","layers-top-right","li","pull-end","pull-start","pulse","rotate-180","rotate-270","rotate-90","rotate-by","shake","spin-pulse","spin-reverse","spin","stack-1x","stack-2x","stack","ul","width-auto","width-fixed",Ie.GROUP,Ie.SWAP_OPACITY,Ie.PRIMARY,Ie.SECONDARY]).concat(Aa.map(function(e){return"".concat(e,"x")})).concat(uo.map(function(e){return"w-".concat(e)})),ho={"Font Awesome 5 Free":{900:"fas",400:"far"},"Font Awesome 5 Pro":{900:"fas",400:"far",normal:"far",300:"fal"},"Font Awesome 5 Brands":{400:"fab",normal:"fab"},"Font Awesome 5 Duotone":{900:"fad"}},R="___FONT_AWESOME___",ut=16,xa="fa",Ia="svg-inline--fa",Y="data-fa-i2svg",dt="data-fa-pseudo-element",go="data-fa-pseudo-element-pending",Ct="data-prefix",kt="data-icon",Cn="fontawesome-i2svg",vo="async",yo=["HTML","HEAD","STYLE","SCRIPT"],Ca=["::before","::after",":before",":after"],ka=(function(){try{return!0}catch{return!1}})();function pe(e){return new Proxy(e,{get:function(t,n){return n in t?t[n]:t[E]}})}var Ta=f({},ta);Ta[E]=f(f(f(f({},{"fa-duotone":"duotone"}),ta[E]),xn.kit),xn["kit-duotone"]);var bo=pe(Ta),mt=f({},fi);mt[E]=f(f(f(f({},{duotone:"fad"}),mt[E]),In.kit),In["kit-duotone"]);var kn=pe(mt),pt=f({},ct);pt[E]=f(f({},pt[E]),vi.kit);var Tt=pe(pt),ht=f({},so);ht[E]=f(f({},ht[E]),hi.kit);var ff=pe(ht),So=jr,Ma="fa-layers-text",wo=zr,Eo=f({},oi),cf=pe(Eo),Ao=["class","data-prefix","data-icon","data-fa-transform","data-fa-mask"],rt=$r,xo=[].concat(O(ci),O(po)),ce=$.FontAwesomeConfig||{};function Io(e){var a=v.querySelector("script["+e+"]");if(a)return a.getAttribute(e)}function Co(e){return e===""?!0:e==="false"?!1:e==="true"?!0:e}v&&typeof v.querySelector=="function"&&(Tn=[["data-family-prefix","familyPrefix"],["data-css-prefix","cssPrefix"],["data-family-default","familyDefault"],["data-style-default","styleDefault"],["data-replacement-class","replacementClass"],["data-auto-replace-svg","autoReplaceSvg"],["data-auto-add-css","autoAddCss"],["data-search-pseudo-elements","searchPseudoElements"],["data-search-pseudo-elements-warnings","searchPseudoElementsWarnings"],["data-search-pseudo-elements-full-scan","searchPseudoElementsFullScan"],["data-observe-mutations","observeMutations"],["data-mutate-approach","mutateApproach"],["data-keep-original-source","keepOriginalSource"],["data-measure-performance","measurePerformance"],["data-show-missing-icons","showMissingIcons"]],Tn.forEach(function(e){var a=De(e,2),t=a[0],n=a[1],r=Co(Io(t));r!=null&&(ce[n]=r)}));var Tn,_a={styleDefault:"solid",familyDefault:E,cssPrefix:xa,replacementClass:Ia,autoReplaceSvg:!0,autoAddCss:!0,searchPseudoElements:!1,searchPseudoElementsWarnings:!0,searchPseudoElementsFullScan:!1,observeMutations:!0,mutateApproach:"async",keepOriginalSource:!0,measurePerformance:!1,showMissingIcons:!0};ce.familyPrefix&&(ce.cssPrefix=ce.familyPrefix);var q=f(f({},_a),ce);q.autoReplaceSvg||(q.observeMutations=!1);var m={};Object.keys(_a).forEach(function(e){Object.defineProperty(m,e,{enumerable:!0,set:function(t){q[e]=t,ue.forEach(function(n){return n(m)})},get:function(){return q[e]}})});Object.defineProperty(m,"familyPrefix",{enumerable:!0,set:function(a){q.cssPrefix=a,ue.forEach(function(t){return t(m)})},get:function(){return q.cssPrefix}});$.FontAwesomeConfig=m;var ue=[];function ko(e){return ue.push(e),function(){ue.splice(ue.indexOf(e),1)}}var z=ut,D={size:16,x:0,y:0,rotate:0,flipX:!1,flipY:!1};function To(e){if(!(!e||!L)){var a=v.createElement("style");a.setAttribute("type","text/css"),a.innerHTML=e;for(var t=v.head.childNodes,n=null,r=t.length-1;r>-1;r--){var i=t[r],o=(i.tagName||"").toUpperCase();["STYLE","LINK"].indexOf(o)>-1&&(n=i)}return v.head.insertBefore(a,n),e}}var Mo="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";function Mn(){for(var e=12,a="";e-- >0;)a+=Mo[Math.random()*62|0];return a}function Q(e){for(var a=[],t=(e||[]).length>>>0;t--;)a[t]=e[t];return a}function Mt(e){return e.classList?Q(e.classList):(e.getAttribute("class")||"").split(" ").filter(function(a){return a})}function Oa(e){return"".concat(e).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/'/g,"&#39;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}function _o(e){return Object.keys(e||{}).reduce(function(a,t){return a+"".concat(t,'="').concat(Oa(e[t]),'" ')},"").trim()}function Pe(e){return Object.keys(e||{}).reduce(function(a,t){return a+"".concat(t,": ").concat(e[t].trim(),";")},"")}function _t(e){return e.size!==D.size||e.x!==D.x||e.y!==D.y||e.rotate!==D.rotate||e.flipX||e.flipY}function Oo(e){var a=e.transform,t=e.containerWidth,n=e.iconWidth,r={transform:"translate(".concat(t/2," 256)")},i="translate(".concat(a.x*32,", ").concat(a.y*32,") "),o="scale(".concat(a.size/16*(a.flipX?-1:1),", ").concat(a.size/16*(a.flipY?-1:1),") "),s="rotate(".concat(a.rotate," 0 0)"),l={transform:"".concat(i," ").concat(o," ").concat(s)},c={transform:"translate(".concat(n/2*-1," -256)")};return{outer:r,inner:l,path:c}}function Do(e){var a=e.transform,t=e.width,n=t===void 0?ut:t,r=e.height,i=r===void 0?ut:r,o=e.startCentered,s=o===void 0?!1:o,l="";return s&&ea?l+="translate(".concat(a.x/z-n/2,"em, ").concat(a.y/z-i/2,"em) "):s?l+="translate(calc(-50% + ".concat(a.x/z,"em), calc(-50% + ").concat(a.y/z,"em)) "):l+="translate(".concat(a.x/z,"em, ").concat(a.y/z,"em) "),l+="scale(".concat(a.size/z*(a.flipX?-1:1),", ").concat(a.size/z*(a.flipY?-1:1),") "),l+="rotate(".concat(a.rotate,"deg) "),l}var Po=`:root, :host {
  --fa-font-solid: normal 900 1em/1 'Font Awesome 7 Free';
  --fa-font-regular: normal 400 1em/1 'Font Awesome 7 Free';
  --fa-font-light: normal 300 1em/1 'Font Awesome 7 Pro';
  --fa-font-thin: normal 100 1em/1 'Font Awesome 7 Pro';
  --fa-font-duotone: normal 900 1em/1 'Font Awesome 7 Duotone';
  --fa-font-duotone-regular: normal 400 1em/1 'Font Awesome 7 Duotone';
  --fa-font-duotone-light: normal 300 1em/1 'Font Awesome 7 Duotone';
  --fa-font-duotone-thin: normal 100 1em/1 'Font Awesome 7 Duotone';
  --fa-font-brands: normal 400 1em/1 'Font Awesome 7 Brands';
  --fa-font-sharp-solid: normal 900 1em/1 'Font Awesome 7 Sharp';
  --fa-font-sharp-regular: normal 400 1em/1 'Font Awesome 7 Sharp';
  --fa-font-sharp-light: normal 300 1em/1 'Font Awesome 7 Sharp';
  --fa-font-sharp-thin: normal 100 1em/1 'Font Awesome 7 Sharp';
  --fa-font-sharp-duotone-solid: normal 900 1em/1 'Font Awesome 7 Sharp Duotone';
  --fa-font-sharp-duotone-regular: normal 400 1em/1 'Font Awesome 7 Sharp Duotone';
  --fa-font-sharp-duotone-light: normal 300 1em/1 'Font Awesome 7 Sharp Duotone';
  --fa-font-sharp-duotone-thin: normal 100 1em/1 'Font Awesome 7 Sharp Duotone';
  --fa-font-slab-regular: normal 400 1em/1 'Font Awesome 7 Slab';
  --fa-font-slab-press-regular: normal 400 1em/1 'Font Awesome 7 Slab Press';
  --fa-font-whiteboard-semibold: normal 600 1em/1 'Font Awesome 7 Whiteboard';
  --fa-font-thumbprint-light: normal 300 1em/1 'Font Awesome 7 Thumbprint';
  --fa-font-notdog-solid: normal 900 1em/1 'Font Awesome 7 Notdog';
  --fa-font-notdog-duo-solid: normal 900 1em/1 'Font Awesome 7 Notdog Duo';
  --fa-font-etch-solid: normal 900 1em/1 'Font Awesome 7 Etch';
  --fa-font-graphite-thin: normal 100 1em/1 'Font Awesome 7 Graphite';
  --fa-font-jelly-regular: normal 400 1em/1 'Font Awesome 7 Jelly';
  --fa-font-jelly-fill-regular: normal 400 1em/1 'Font Awesome 7 Jelly Fill';
  --fa-font-jelly-duo-regular: normal 400 1em/1 'Font Awesome 7 Jelly Duo';
  --fa-font-chisel-regular: normal 400 1em/1 'Font Awesome 7 Chisel';
  --fa-font-utility-semibold: normal 600 1em/1 'Font Awesome 7 Utility';
  --fa-font-utility-duo-semibold: normal 600 1em/1 'Font Awesome 7 Utility Duo';
  --fa-font-utility-fill-semibold: normal 600 1em/1 'Font Awesome 7 Utility Fill';
}

.svg-inline--fa {
  box-sizing: content-box;
  display: var(--fa-display, inline-block);
  height: 1em;
  overflow: visible;
  vertical-align: -0.125em;
  width: var(--fa-width, 1.25em);
}
.svg-inline--fa.fa-2xs {
  vertical-align: 0.1em;
}
.svg-inline--fa.fa-xs {
  vertical-align: 0em;
}
.svg-inline--fa.fa-sm {
  vertical-align: -0.0714285714em;
}
.svg-inline--fa.fa-lg {
  vertical-align: -0.2em;
}
.svg-inline--fa.fa-xl {
  vertical-align: -0.25em;
}
.svg-inline--fa.fa-2xl {
  vertical-align: -0.3125em;
}
.svg-inline--fa.fa-pull-left,
.svg-inline--fa .fa-pull-start {
  float: inline-start;
  margin-inline-end: var(--fa-pull-margin, 0.3em);
}
.svg-inline--fa.fa-pull-right,
.svg-inline--fa .fa-pull-end {
  float: inline-end;
  margin-inline-start: var(--fa-pull-margin, 0.3em);
}
.svg-inline--fa.fa-li {
  width: var(--fa-li-width, 2em);
  inset-inline-start: calc(-1 * var(--fa-li-width, 2em));
  inset-block-start: 0.25em; /* syncing vertical alignment with Web Font rendering */
}

.fa-layers-counter, .fa-layers-text {
  display: inline-block;
  position: absolute;
  text-align: center;
}

.fa-layers {
  display: inline-block;
  height: 1em;
  position: relative;
  text-align: center;
  vertical-align: -0.125em;
  width: var(--fa-width, 1.25em);
}
.fa-layers .svg-inline--fa {
  inset: 0;
  margin: auto;
  position: absolute;
  transform-origin: center center;
}

.fa-layers-text {
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  transform-origin: center center;
}

.fa-layers-counter {
  background-color: var(--fa-counter-background-color, #ff253a);
  border-radius: var(--fa-counter-border-radius, 1em);
  box-sizing: border-box;
  color: var(--fa-inverse, #fff);
  line-height: var(--fa-counter-line-height, 1);
  max-width: var(--fa-counter-max-width, 5em);
  min-width: var(--fa-counter-min-width, 1.5em);
  overflow: hidden;
  padding: var(--fa-counter-padding, 0.25em 0.5em);
  right: var(--fa-right, 0);
  text-overflow: ellipsis;
  top: var(--fa-top, 0);
  transform: scale(var(--fa-counter-scale, 0.25));
  transform-origin: top right;
}

.fa-layers-bottom-right {
  bottom: var(--fa-bottom, 0);
  right: var(--fa-right, 0);
  top: auto;
  transform: scale(var(--fa-layers-scale, 0.25));
  transform-origin: bottom right;
}

.fa-layers-bottom-left {
  bottom: var(--fa-bottom, 0);
  left: var(--fa-left, 0);
  right: auto;
  top: auto;
  transform: scale(var(--fa-layers-scale, 0.25));
  transform-origin: bottom left;
}

.fa-layers-top-right {
  top: var(--fa-top, 0);
  right: var(--fa-right, 0);
  transform: scale(var(--fa-layers-scale, 0.25));
  transform-origin: top right;
}

.fa-layers-top-left {
  left: var(--fa-left, 0);
  right: auto;
  top: var(--fa-top, 0);
  transform: scale(var(--fa-layers-scale, 0.25));
  transform-origin: top left;
}

.fa-1x {
  font-size: 1em;
}

.fa-2x {
  font-size: 2em;
}

.fa-3x {
  font-size: 3em;
}

.fa-4x {
  font-size: 4em;
}

.fa-5x {
  font-size: 5em;
}

.fa-6x {
  font-size: 6em;
}

.fa-7x {
  font-size: 7em;
}

.fa-8x {
  font-size: 8em;
}

.fa-9x {
  font-size: 9em;
}

.fa-10x {
  font-size: 10em;
}

.fa-2xs {
  font-size: calc(10 / 16 * 1em); /* converts a 10px size into an em-based value that's relative to the scale's 16px base */
  line-height: calc(1 / 10 * 1em); /* sets the line-height of the icon back to that of it's parent */
  vertical-align: calc((6 / 10 - 0.375) * 1em); /* vertically centers the icon taking into account the surrounding text's descender */
}

.fa-xs {
  font-size: calc(12 / 16 * 1em); /* converts a 12px size into an em-based value that's relative to the scale's 16px base */
  line-height: calc(1 / 12 * 1em); /* sets the line-height of the icon back to that of it's parent */
  vertical-align: calc((6 / 12 - 0.375) * 1em); /* vertically centers the icon taking into account the surrounding text's descender */
}

.fa-sm {
  font-size: calc(14 / 16 * 1em); /* converts a 14px size into an em-based value that's relative to the scale's 16px base */
  line-height: calc(1 / 14 * 1em); /* sets the line-height of the icon back to that of it's parent */
  vertical-align: calc((6 / 14 - 0.375) * 1em); /* vertically centers the icon taking into account the surrounding text's descender */
}

.fa-lg {
  font-size: calc(20 / 16 * 1em); /* converts a 20px size into an em-based value that's relative to the scale's 16px base */
  line-height: calc(1 / 20 * 1em); /* sets the line-height of the icon back to that of it's parent */
  vertical-align: calc((6 / 20 - 0.375) * 1em); /* vertically centers the icon taking into account the surrounding text's descender */
}

.fa-xl {
  font-size: calc(24 / 16 * 1em); /* converts a 24px size into an em-based value that's relative to the scale's 16px base */
  line-height: calc(1 / 24 * 1em); /* sets the line-height of the icon back to that of it's parent */
  vertical-align: calc((6 / 24 - 0.375) * 1em); /* vertically centers the icon taking into account the surrounding text's descender */
}

.fa-2xl {
  font-size: calc(32 / 16 * 1em); /* converts a 32px size into an em-based value that's relative to the scale's 16px base */
  line-height: calc(1 / 32 * 1em); /* sets the line-height of the icon back to that of it's parent */
  vertical-align: calc((6 / 32 - 0.375) * 1em); /* vertically centers the icon taking into account the surrounding text's descender */
}

.fa-width-auto {
  --fa-width: auto;
}

.fa-fw,
.fa-width-fixed {
  --fa-width: 1.25em;
}

.fa-ul {
  list-style-type: none;
  margin-inline-start: var(--fa-li-margin, 2.5em);
  padding-inline-start: 0;
}
.fa-ul > li {
  position: relative;
}

.fa-li {
  inset-inline-start: calc(-1 * var(--fa-li-width, 2em));
  position: absolute;
  text-align: center;
  width: var(--fa-li-width, 2em);
  line-height: inherit;
}

/* Heads Up: Bordered Icons will not be supported in the future!
  - This feature will be deprecated in the next major release of Font Awesome (v8)!
  - You may continue to use it in this version *v7), but it will not be supported in Font Awesome v8.
*/
/* Notes:
* --@{v.$css-prefix}-border-width = 1/16 by default (to render as ~1px based on a 16px default font-size)
* --@{v.$css-prefix}-border-padding =
  ** 3/16 for vertical padding (to give ~2px of vertical whitespace around an icon considering it's vertical alignment)
  ** 4/16 for horizontal padding (to give ~4px of horizontal whitespace around an icon)
*/
.fa-border {
  border-color: var(--fa-border-color, #eee);
  border-radius: var(--fa-border-radius, 0.1em);
  border-style: var(--fa-border-style, solid);
  border-width: var(--fa-border-width, 0.0625em);
  box-sizing: var(--fa-border-box-sizing, content-box);
  padding: var(--fa-border-padding, 0.1875em 0.25em);
}

.fa-pull-left,
.fa-pull-start {
  float: inline-start;
  margin-inline-end: var(--fa-pull-margin, 0.3em);
}

.fa-pull-right,
.fa-pull-end {
  float: inline-end;
  margin-inline-start: var(--fa-pull-margin, 0.3em);
}

.fa-beat {
  animation-name: fa-beat;
  animation-delay: var(--fa-animation-delay, 0s);
  animation-direction: var(--fa-animation-direction, normal);
  animation-duration: var(--fa-animation-duration, 1s);
  animation-iteration-count: var(--fa-animation-iteration-count, infinite);
  animation-timing-function: var(--fa-animation-timing, ease-in-out);
}

.fa-bounce {
  animation-name: fa-bounce;
  animation-delay: var(--fa-animation-delay, 0s);
  animation-direction: var(--fa-animation-direction, normal);
  animation-duration: var(--fa-animation-duration, 1s);
  animation-iteration-count: var(--fa-animation-iteration-count, infinite);
  animation-timing-function: var(--fa-animation-timing, cubic-bezier(0.28, 0.84, 0.42, 1));
}

.fa-fade {
  animation-name: fa-fade;
  animation-delay: var(--fa-animation-delay, 0s);
  animation-direction: var(--fa-animation-direction, normal);
  animation-duration: var(--fa-animation-duration, 1s);
  animation-iteration-count: var(--fa-animation-iteration-count, infinite);
  animation-timing-function: var(--fa-animation-timing, cubic-bezier(0.4, 0, 0.6, 1));
}

.fa-beat-fade {
  animation-name: fa-beat-fade;
  animation-delay: var(--fa-animation-delay, 0s);
  animation-direction: var(--fa-animation-direction, normal);
  animation-duration: var(--fa-animation-duration, 1s);
  animation-iteration-count: var(--fa-animation-iteration-count, infinite);
  animation-timing-function: var(--fa-animation-timing, cubic-bezier(0.4, 0, 0.6, 1));
}

.fa-flip {
  animation-name: fa-flip;
  animation-delay: var(--fa-animation-delay, 0s);
  animation-direction: var(--fa-animation-direction, normal);
  animation-duration: var(--fa-animation-duration, 1s);
  animation-iteration-count: var(--fa-animation-iteration-count, infinite);
  animation-timing-function: var(--fa-animation-timing, ease-in-out);
}

.fa-shake {
  animation-name: fa-shake;
  animation-delay: var(--fa-animation-delay, 0s);
  animation-direction: var(--fa-animation-direction, normal);
  animation-duration: var(--fa-animation-duration, 1s);
  animation-iteration-count: var(--fa-animation-iteration-count, infinite);
  animation-timing-function: var(--fa-animation-timing, linear);
}

.fa-spin {
  animation-name: fa-spin;
  animation-delay: var(--fa-animation-delay, 0s);
  animation-direction: var(--fa-animation-direction, normal);
  animation-duration: var(--fa-animation-duration, 2s);
  animation-iteration-count: var(--fa-animation-iteration-count, infinite);
  animation-timing-function: var(--fa-animation-timing, linear);
}

.fa-spin-reverse {
  --fa-animation-direction: reverse;
}

.fa-pulse,
.fa-spin-pulse {
  animation-name: fa-spin;
  animation-direction: var(--fa-animation-direction, normal);
  animation-duration: var(--fa-animation-duration, 1s);
  animation-iteration-count: var(--fa-animation-iteration-count, infinite);
  animation-timing-function: var(--fa-animation-timing, steps(8));
}

@media (prefers-reduced-motion: reduce) {
  .fa-beat,
  .fa-bounce,
  .fa-fade,
  .fa-beat-fade,
  .fa-flip,
  .fa-pulse,
  .fa-shake,
  .fa-spin,
  .fa-spin-pulse {
    animation: none !important;
    transition: none !important;
  }
}
@keyframes fa-beat {
  0%, 90% {
    transform: scale(1);
  }
  45% {
    transform: scale(var(--fa-beat-scale, 1.25));
  }
}
@keyframes fa-bounce {
  0% {
    transform: scale(1, 1) translateY(0);
  }
  10% {
    transform: scale(var(--fa-bounce-start-scale-x, 1.1), var(--fa-bounce-start-scale-y, 0.9)) translateY(0);
  }
  30% {
    transform: scale(var(--fa-bounce-jump-scale-x, 0.9), var(--fa-bounce-jump-scale-y, 1.1)) translateY(var(--fa-bounce-height, -0.5em));
  }
  50% {
    transform: scale(var(--fa-bounce-land-scale-x, 1.05), var(--fa-bounce-land-scale-y, 0.95)) translateY(0);
  }
  57% {
    transform: scale(1, 1) translateY(var(--fa-bounce-rebound, -0.125em));
  }
  64% {
    transform: scale(1, 1) translateY(0);
  }
  100% {
    transform: scale(1, 1) translateY(0);
  }
}
@keyframes fa-fade {
  50% {
    opacity: var(--fa-fade-opacity, 0.4);
  }
}
@keyframes fa-beat-fade {
  0%, 100% {
    opacity: var(--fa-beat-fade-opacity, 0.4);
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(var(--fa-beat-fade-scale, 1.125));
  }
}
@keyframes fa-flip {
  50% {
    transform: rotate3d(var(--fa-flip-x, 0), var(--fa-flip-y, 1), var(--fa-flip-z, 0), var(--fa-flip-angle, -180deg));
  }
}
@keyframes fa-shake {
  0% {
    transform: rotate(-15deg);
  }
  4% {
    transform: rotate(15deg);
  }
  8%, 24% {
    transform: rotate(-18deg);
  }
  12%, 28% {
    transform: rotate(18deg);
  }
  16% {
    transform: rotate(-22deg);
  }
  20% {
    transform: rotate(22deg);
  }
  32% {
    transform: rotate(-12deg);
  }
  36% {
    transform: rotate(12deg);
  }
  40%, 100% {
    transform: rotate(0deg);
  }
}
@keyframes fa-spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
.fa-rotate-90 {
  transform: rotate(90deg);
}

.fa-rotate-180 {
  transform: rotate(180deg);
}

.fa-rotate-270 {
  transform: rotate(270deg);
}

.fa-flip-horizontal {
  transform: scale(-1, 1);
}

.fa-flip-vertical {
  transform: scale(1, -1);
}

.fa-flip-both,
.fa-flip-horizontal.fa-flip-vertical {
  transform: scale(-1, -1);
}

.fa-rotate-by {
  transform: rotate(var(--fa-rotate-angle, 0));
}

.svg-inline--fa .fa-primary {
  fill: var(--fa-primary-color, currentColor);
  opacity: var(--fa-primary-opacity, 1);
}

.svg-inline--fa .fa-secondary {
  fill: var(--fa-secondary-color, currentColor);
  opacity: var(--fa-secondary-opacity, 0.4);
}

.svg-inline--fa.fa-swap-opacity .fa-primary {
  opacity: var(--fa-secondary-opacity, 0.4);
}

.svg-inline--fa.fa-swap-opacity .fa-secondary {
  opacity: var(--fa-primary-opacity, 1);
}

.svg-inline--fa mask .fa-primary,
.svg-inline--fa mask .fa-secondary {
  fill: black;
}

.svg-inline--fa.fa-inverse {
  fill: var(--fa-inverse, #fff);
}

.fa-stack {
  display: inline-block;
  height: 2em;
  line-height: 2em;
  position: relative;
  vertical-align: middle;
  width: 2.5em;
}

.fa-inverse {
  color: var(--fa-inverse, #fff);
}

.svg-inline--fa.fa-stack-1x {
  --fa-width: 1.25em;
  height: 1em;
  width: var(--fa-width);
}
.svg-inline--fa.fa-stack-2x {
  --fa-width: 2.5em;
  height: 2em;
  width: var(--fa-width);
}

.fa-stack-1x,
.fa-stack-2x {
  inset: 0;
  margin: auto;
  position: absolute;
  z-index: var(--fa-stack-z-index, auto);
}`;function Da(){var e=xa,a=Ia,t=m.cssPrefix,n=m.replacementClass,r=Po;if(t!==e||n!==a){var i=new RegExp("\\.".concat(e,"\\-"),"g"),o=new RegExp("\\--".concat(e,"\\-"),"g"),s=new RegExp("\\.".concat(a),"g");r=r.replace(i,".".concat(t,"-")).replace(o,"--".concat(t,"-")).replace(s,".".concat(n))}return r}var _n=!1;function it(){m.autoAddCss&&!_n&&(To(Da()),_n=!0)}var No={mixout:function(){return{dom:{css:Da,insertCss:it}}},hooks:function(){return{beforeDOMElementCreation:function(){it()},beforeI2svg:function(){it()}}}},F=$||{};F[R]||(F[R]={});F[R].styles||(F[R].styles={});F[R].hooks||(F[R].hooks={});F[R].shims||(F[R].shims=[]);var _=F[R],Pa=[],Na=function(){v.removeEventListener("DOMContentLoaded",Na),_e=1,Pa.map(function(a){return a()})},_e=!1;L&&(_e=(v.documentElement.doScroll?/^loaded|^c/:/^loaded|^i|^c/).test(v.readyState),_e||v.addEventListener("DOMContentLoaded",Na));function Ro(e){L&&(_e?setTimeout(e,0):Pa.push(e))}function he(e){var a=e.tag,t=e.attributes,n=t===void 0?{}:t,r=e.children,i=r===void 0?[]:r;return typeof e=="string"?Oa(e):"<".concat(a," ").concat(_o(n),">").concat(i.map(he).join(""),"</").concat(a,">")}function On(e,a,t){if(e&&e[a]&&e[a][t])return{prefix:a,iconName:t,icon:e[a][t]}}var Fo=function(a,t){return function(n,r,i,o){return a.call(t,n,r,i,o)}},ot=function(a,t,n,r){var i=Object.keys(a),o=i.length,s=r!==void 0?Fo(t,r):t,l,c,u;for(n===void 0?(l=1,u=a[i[0]]):(l=0,u=n);l<o;l++)c=i[l],u=s(u,a[c],c,a);return u};function Ra(e){return O(e).length!==1?null:e.codePointAt(0).toString(16)}function Dn(e){return Object.keys(e).reduce(function(a,t){var n=e[t],r=!!n.icon;return r?a[n.iconName]=n.icon:a[t]=n,a},{})}function gt(e,a){var t=arguments.length>2&&arguments[2]!==void 0?arguments[2]:{},n=t.skipHooks,r=n===void 0?!1:n,i=Dn(a);typeof _.hooks.addPack=="function"&&!r?_.hooks.addPack(e,Dn(a)):_.styles[e]=f(f({},_.styles[e]||{}),i),e==="fas"&&gt("fa",a)}var de=_.styles,Lo=_.shims,Fa=Object.keys(Tt),jo=Fa.reduce(function(e,a){return e[a]=Object.keys(Tt[a]),e},{}),Ot=null,La={},ja={},za={},$a={},Ha={};function zo(e){return~xo.indexOf(e)}function $o(e,a){var t=a.split("-"),n=t[0],r=t.slice(1).join("-");return n===e&&r!==""&&!zo(r)?r:null}var Ua=function(){var a=function(i){return ot(de,function(o,s,l){return o[l]=ot(s,i,{}),o},{})};La=a(function(r,i,o){if(i[3]&&(r[i[3]]=o),i[2]){var s=i[2].filter(function(l){return typeof l=="number"});s.forEach(function(l){r[l.toString(16)]=o})}return r}),ja=a(function(r,i,o){if(r[o]=o,i[2]){var s=i[2].filter(function(l){return typeof l=="string"});s.forEach(function(l){r[l]=o})}return r}),Ha=a(function(r,i,o){var s=i[2];return r[o]=o,s.forEach(function(l){r[l]=o}),r});var t="far"in de||m.autoFetchSvg,n=ot(Lo,function(r,i){var o=i[0],s=i[1],l=i[2];return s==="far"&&!t&&(s="fas"),typeof o=="string"&&(r.names[o]={prefix:s,iconName:l}),typeof o=="number"&&(r.unicodes[o.toString(16)]={prefix:s,iconName:l}),r},{names:{},unicodes:{}});za=n.names,$a=n.unicodes,Ot=Ne(m.styleDefault,{family:m.familyDefault})};ko(function(e){Ot=Ne(e.styleDefault,{family:m.familyDefault})});Ua();function Dt(e,a){return(La[e]||{})[a]}function Ho(e,a){return(ja[e]||{})[a]}function B(e,a){return(Ha[e]||{})[a]}function Wa(e){return za[e]||{prefix:null,iconName:null}}function Uo(e){var a=$a[e],t=Dt("fas",e);return a||(t?{prefix:"fas",iconName:t}:null)||{prefix:null,iconName:null}}function H(){return Ot}var Ba=function(){return{prefix:null,iconName:null,rest:[]}};function Wo(e){var a=E,t=Fa.reduce(function(n,r){return n[r]="".concat(m.cssPrefix,"-").concat(r),n},{});return Sa.forEach(function(n){(e.includes(t[n])||e.some(function(r){return jo[n].includes(r)}))&&(a=n)}),a}function Ne(e){var a=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},t=a.family,n=t===void 0?E:t,r=bo[n][e];if(n===me&&!e)return"fad";var i=kn[n][e]||kn[n][r],o=e in _.styles?e:null,s=i||o||null;return s}function Bo(e){var a=[],t=null;return e.forEach(function(n){var r=$o(m.cssPrefix,n);r?t=r:n&&a.push(n)}),{iconName:t,rest:a}}function Pn(e){return e.sort().filter(function(a,t,n){return n.indexOf(a)===t})}var Nn=Ea.concat(wa);function Re(e){var a=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},t=a.skipLookups,n=t===void 0?!1:t,r=null,i=Pn(e.filter(function(p){return Nn.includes(p)})),o=Pn(e.filter(function(p){return!Nn.includes(p)})),s=i.filter(function(p){return r=p,!na.includes(p)}),l=De(s,1),c=l[0],u=c===void 0?null:c,d=Wo(i),g=f(f({},Bo(o)),{},{prefix:Ne(u,{family:d})});return f(f(f({},g),Xo({values:e,family:d,styles:de,config:m,canonical:g,givenPrefix:r})),Yo(n,r,g))}function Yo(e,a,t){var n=t.prefix,r=t.iconName;if(e||!n||!r)return{prefix:n,iconName:r};var i=a==="fa"?Wa(r):{},o=B(n,r);return r=i.iconName||o||r,n=i.prefix||n,n==="far"&&!de.far&&de.fas&&!m.autoFetchSvg&&(n="fas"),{prefix:n,iconName:r}}var Vo=Sa.filter(function(e){return e!==E||e!==me}),Go=Object.keys(ct).filter(function(e){return e!==E}).map(function(e){return Object.keys(ct[e])}).flat();function Xo(e){var a=e.values,t=e.family,n=e.canonical,r=e.givenPrefix,i=r===void 0?"":r,o=e.styles,s=o===void 0?{}:o,l=e.config,c=l===void 0?{}:l,u=t===me,d=a.includes("fa-duotone")||a.includes("fad"),g=c.familyDefault==="duotone",p=n.prefix==="fad"||n.prefix==="fa-duotone";if(!u&&(d||g||p)&&(n.prefix="fad"),(a.includes("fa-brands")||a.includes("fab"))&&(n.prefix="fab"),!n.prefix&&Vo.includes(t)){var S=Object.keys(s).find(function(A){return Go.includes(A)});if(S||c.autoFetchSvg){var y=li.get(t).defaultShortPrefixId;n.prefix=y,n.iconName=B(n.prefix,n.iconName)||n.iconName}}return(n.prefix==="fa"||i==="fa")&&(n.prefix=H()||"fas"),n}var Ko=(function(){function e(){_r(this,e),this.definitions={}}return Or(e,[{key:"add",value:function(){for(var t=this,n=arguments.length,r=new Array(n),i=0;i<n;i++)r[i]=arguments[i];var o=r.reduce(this._pullDefinitions,{});Object.keys(o).forEach(function(s){t.definitions[s]=f(f({},t.definitions[s]||{}),o[s]),gt(s,o[s]);var l=Tt[E][s];l&&gt(l,o[s]),Ua()})}},{key:"reset",value:function(){this.definitions={}}},{key:"_pullDefinitions",value:function(t,n){var r=n.prefix&&n.iconName&&n.icon?{0:n}:n;return Object.keys(r).map(function(i){var o=r[i],s=o.prefix,l=o.iconName,c=o.icon,u=c[2];t[s]||(t[s]={}),u.length>0&&u.forEach(function(d){typeof d=="string"&&(t[s][d]=c)}),t[s][l]=c}),t}}])})(),Rn=[],J={},Z={},Jo=Object.keys(Z);function Zo(e,a){var t=a.mixoutsTo;return Rn=e,J={},Object.keys(Z).forEach(function(n){Jo.indexOf(n)===-1&&delete Z[n]}),Rn.forEach(function(n){var r=n.mixout?n.mixout():{};if(Object.keys(r).forEach(function(o){typeof r[o]=="function"&&(t[o]=r[o]),Me(r[o])==="object"&&Object.keys(r[o]).forEach(function(s){t[o]||(t[o]={}),t[o][s]=r[o][s]})}),n.hooks){var i=n.hooks();Object.keys(i).forEach(function(o){J[o]||(J[o]=[]),J[o].push(i[o])})}n.provides&&n.provides(Z)}),t}function vt(e,a){for(var t=arguments.length,n=new Array(t>2?t-2:0),r=2;r<t;r++)n[r-2]=arguments[r];var i=J[e]||[];return i.forEach(function(o){a=o.apply(null,[a].concat(n))}),a}function V(e){for(var a=arguments.length,t=new Array(a>1?a-1:0),n=1;n<a;n++)t[n-1]=arguments[n];var r=J[e]||[];r.forEach(function(i){i.apply(null,t)})}function U(){var e=arguments[0],a=Array.prototype.slice.call(arguments,1);return Z[e]?Z[e].apply(null,a):void 0}function yt(e){e.prefix==="fa"&&(e.prefix="fas");var a=e.iconName,t=e.prefix||H();if(a)return a=B(t,a)||a,On(Ya.definitions,t,a)||On(_.styles,t,a)}var Ya=new Ko,qo=function(){m.autoReplaceSvg=!1,m.observeMutations=!1,V("noAuto")},Qo={i2svg:function(){var a=arguments.length>0&&arguments[0]!==void 0?arguments[0]:{};return L?(V("beforeI2svg",a),U("pseudoElements2svg",a),U("i2svg",a)):Promise.reject(new Error("Operation requires a DOM of some kind."))},watch:function(){var a=arguments.length>0&&arguments[0]!==void 0?arguments[0]:{},t=a.autoReplaceSvgRoot;m.autoReplaceSvg===!1&&(m.autoReplaceSvg=!0),m.observeMutations=!0,Ro(function(){ts({autoReplaceSvgRoot:t}),V("watch",a)})}},es={icon:function(a){if(a===null)return null;if(Me(a)==="object"&&a.prefix&&a.iconName)return{prefix:a.prefix,iconName:B(a.prefix,a.iconName)||a.iconName};if(Array.isArray(a)&&a.length===2){var t=a[1].indexOf("fa-")===0?a[1].slice(3):a[1],n=Ne(a[0]);return{prefix:n,iconName:B(n,t)||t}}if(typeof a=="string"&&(a.indexOf("".concat(m.cssPrefix,"-"))>-1||a.match(So))){var r=Re(a.split(" "),{skipLookups:!0});return{prefix:r.prefix||H(),iconName:B(r.prefix,r.iconName)||r.iconName}}if(typeof a=="string"){var i=H();return{prefix:i,iconName:B(i,a)||a}}}},T={noAuto:qo,config:m,dom:Qo,parse:es,library:Ya,findIconDefinition:yt,toHtml:he},ts=function(){var a=arguments.length>0&&arguments[0]!==void 0?arguments[0]:{},t=a.autoReplaceSvgRoot,n=t===void 0?v:t;(Object.keys(_.styles).length>0||m.autoFetchSvg)&&L&&m.autoReplaceSvg&&T.dom.i2svg({node:n})};function Fe(e,a){return Object.defineProperty(e,"abstract",{get:a}),Object.defineProperty(e,"html",{get:function(){return e.abstract.map(function(n){return he(n)})}}),Object.defineProperty(e,"node",{get:function(){if(L){var n=v.createElement("div");return n.innerHTML=e.html,n.children}}}),e}function ns(e){var a=e.children,t=e.main,n=e.mask,r=e.attributes,i=e.styles,o=e.transform;if(_t(o)&&t.found&&!n.found){var s=t.width,l=t.height,c={x:s/l/2,y:.5};r.style=Pe(f(f({},i),{},{"transform-origin":"".concat(c.x+o.x/16,"em ").concat(c.y+o.y/16,"em")}))}return[{tag:"svg",attributes:r,children:a}]}function as(e){var a=e.prefix,t=e.iconName,n=e.children,r=e.attributes,i=e.symbol,o=i===!0?"".concat(a,"-").concat(m.cssPrefix,"-").concat(t):i;return[{tag:"svg",attributes:{style:"display: none;"},children:[{tag:"symbol",attributes:f(f({},r),{},{id:o}),children:n}]}]}function rs(e){var a=["aria-label","aria-labelledby","title","role"];return a.some(function(t){return t in e})}function Pt(e){var a=e.icons,t=a.main,n=a.mask,r=e.prefix,i=e.iconName,o=e.transform,s=e.symbol,l=e.maskId,c=e.extra,u=e.watchable,d=u===void 0?!1:u,g=n.found?n:t,p=g.width,S=g.height,y=[m.replacementClass,i?"".concat(m.cssPrefix,"-").concat(i):""].filter(function(P){return c.classes.indexOf(P)===-1}).filter(function(P){return P!==""||!!P}).concat(c.classes).join(" "),A={children:[],attributes:f(f({},c.attributes),{},{"data-prefix":r,"data-icon":i,class:y,role:c.attributes.role||"img",viewBox:"0 0 ".concat(p," ").concat(S)})};!rs(c.attributes)&&!c.attributes["aria-hidden"]&&(A.attributes["aria-hidden"]="true"),d&&(A.attributes[Y]="");var w=f(f({},A),{},{prefix:r,iconName:i,main:t,mask:n,maskId:l,transform:o,symbol:s,styles:f({},c.styles)}),C=n.found&&t.found?U("generateAbstractMask",w)||{children:[],attributes:{}}:U("generateAbstractIcon",w)||{children:[],attributes:{}},M=C.children,G=C.attributes;return w.children=M,w.attributes=G,s?as(w):ns(w)}function Fn(e){var a=e.content,t=e.width,n=e.height,r=e.transform,i=e.extra,o=e.watchable,s=o===void 0?!1:o,l=f(f({},i.attributes),{},{class:i.classes.join(" ")});s&&(l[Y]="");var c=f({},i.styles);_t(r)&&(c.transform=Do({transform:r,startCentered:!0,width:t,height:n}),c["-webkit-transform"]=c.transform);var u=Pe(c);u.length>0&&(l.style=u);var d=[];return d.push({tag:"span",attributes:l,children:[a]}),d}function is(e){var a=e.content,t=e.extra,n=f(f({},t.attributes),{},{class:t.classes.join(" ")}),r=Pe(t.styles);r.length>0&&(n.style=r);var i=[];return i.push({tag:"span",attributes:n,children:[a]}),i}var st=_.styles;function bt(e){var a=e[0],t=e[1],n=e.slice(4),r=De(n,1),i=r[0],o=null;return Array.isArray(i)?o={tag:"g",attributes:{class:"".concat(m.cssPrefix,"-").concat(rt.GROUP)},children:[{tag:"path",attributes:{class:"".concat(m.cssPrefix,"-").concat(rt.SECONDARY),fill:"currentColor",d:i[0]}},{tag:"path",attributes:{class:"".concat(m.cssPrefix,"-").concat(rt.PRIMARY),fill:"currentColor",d:i[1]}}]}:o={tag:"path",attributes:{fill:"currentColor",d:i}},{found:!0,width:a,height:t,icon:o}}var os={found:!1,width:512,height:512};function ss(e,a){!ka&&!m.showMissingIcons&&e&&console.error('Icon with name "'.concat(e,'" and prefix "').concat(a,'" is missing.'))}function St(e,a){var t=a;return a==="fa"&&m.styleDefault!==null&&(a=H()),new Promise(function(n,r){if(t==="fa"){var i=Wa(e)||{};e=i.iconName||e,a=i.prefix||a}if(e&&a&&st[a]&&st[a][e]){var o=st[a][e];return n(bt(o))}ss(e,a),n(f(f({},os),{},{icon:m.showMissingIcons&&e?U("missingIconAbstract")||{}:{}}))})}var Ln=function(){},wt=m.measurePerformance&&xe&&xe.mark&&xe.measure?xe:{mark:Ln,measure:Ln},fe='FA "7.2.0"',ls=function(a){return wt.mark("".concat(fe," ").concat(a," begins")),function(){return Va(a)}},Va=function(a){wt.mark("".concat(fe," ").concat(a," ends")),wt.measure("".concat(fe," ").concat(a),"".concat(fe," ").concat(a," begins"),"".concat(fe," ").concat(a," ends"))},Nt={begin:ls,end:Va},ke=function(){};function jn(e){var a=e.getAttribute?e.getAttribute(Y):null;return typeof a=="string"}function fs(e){var a=e.getAttribute?e.getAttribute(Ct):null,t=e.getAttribute?e.getAttribute(kt):null;return a&&t}function cs(e){return e&&e.classList&&e.classList.contains&&e.classList.contains(m.replacementClass)}function us(){if(m.autoReplaceSvg===!0)return Te.replace;var e=Te[m.autoReplaceSvg];return e||Te.replace}function ds(e){return v.createElementNS("http://www.w3.org/2000/svg",e)}function ms(e){return v.createElement(e)}function Ga(e){var a=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},t=a.ceFn,n=t===void 0?e.tag==="svg"?ds:ms:t;if(typeof e=="string")return v.createTextNode(e);var r=n(e.tag);Object.keys(e.attributes||[]).forEach(function(o){r.setAttribute(o,e.attributes[o])});var i=e.children||[];return i.forEach(function(o){r.appendChild(Ga(o,{ceFn:n}))}),r}function ps(e){var a=" ".concat(e.outerHTML," ");return a="".concat(a,"Font Awesome fontawesome.com "),a}var Te={replace:function(a){var t=a[0];if(t.parentNode)if(a[1].forEach(function(r){t.parentNode.insertBefore(Ga(r),t)}),t.getAttribute(Y)===null&&m.keepOriginalSource){var n=v.createComment(ps(t));t.parentNode.replaceChild(n,t)}else t.remove()},nest:function(a){var t=a[0],n=a[1];if(~Mt(t).indexOf(m.replacementClass))return Te.replace(a);var r=new RegExp("".concat(m.cssPrefix,"-.*"));if(delete n[0].attributes.id,n[0].attributes.class){var i=n[0].attributes.class.split(" ").reduce(function(s,l){return l===m.replacementClass||l.match(r)?s.toSvg.push(l):s.toNode.push(l),s},{toNode:[],toSvg:[]});n[0].attributes.class=i.toSvg.join(" "),i.toNode.length===0?t.removeAttribute("class"):t.setAttribute("class",i.toNode.join(" "))}var o=n.map(function(s){return he(s)}).join(`
`);t.setAttribute(Y,""),t.innerHTML=o}};function zn(e){e()}function Xa(e,a){var t=typeof a=="function"?a:ke;if(e.length===0)t();else{var n=zn;m.mutateApproach===vo&&(n=$.requestAnimationFrame||zn),n(function(){var r=us(),i=Nt.begin("mutate");e.map(r),i(),t()})}}var Rt=!1;function Ka(){Rt=!0}function Et(){Rt=!1}var Oe=null;function $n(e){if(An&&m.observeMutations){var a=e.treeCallback,t=a===void 0?ke:a,n=e.nodeCallback,r=n===void 0?ke:n,i=e.pseudoElementsCallback,o=i===void 0?ke:i,s=e.observeMutationsRoot,l=s===void 0?v:s;Oe=new An(function(c){if(!Rt){var u=H();Q(c).forEach(function(d){if(d.type==="childList"&&d.addedNodes.length>0&&!jn(d.addedNodes[0])&&(m.searchPseudoElements&&o(d.target),t(d.target)),d.type==="attributes"&&d.target.parentNode&&m.searchPseudoElements&&o([d.target],!0),d.type==="attributes"&&jn(d.target)&&~Ao.indexOf(d.attributeName))if(d.attributeName==="class"&&fs(d.target)){var g=Re(Mt(d.target)),p=g.prefix,S=g.iconName;d.target.setAttribute(Ct,p||u),S&&d.target.setAttribute(kt,S)}else cs(d.target)&&r(d.target)})}}),L&&Oe.observe(l,{childList:!0,attributes:!0,characterData:!0,subtree:!0})}}function hs(){Oe&&Oe.disconnect()}function gs(e){var a=e.getAttribute("style"),t=[];return a&&(t=a.split(";").reduce(function(n,r){var i=r.split(":"),o=i[0],s=i.slice(1);return o&&s.length>0&&(n[o]=s.join(":").trim()),n},{})),t}function vs(e){var a=e.getAttribute("data-prefix"),t=e.getAttribute("data-icon"),n=e.innerText!==void 0?e.innerText.trim():"",r=Re(Mt(e));return r.prefix||(r.prefix=H()),a&&t&&(r.prefix=a,r.iconName=t),r.iconName&&r.prefix||(r.prefix&&n.length>0&&(r.iconName=Ho(r.prefix,e.innerText)||Dt(r.prefix,Ra(e.innerText))),!r.iconName&&m.autoFetchSvg&&e.firstChild&&e.firstChild.nodeType===Node.TEXT_NODE&&(r.iconName=e.firstChild.data)),r}function ys(e){var a=Q(e.attributes).reduce(function(t,n){return t.name!=="class"&&t.name!=="style"&&(t[n.name]=n.value),t},{});return a}function bs(){return{iconName:null,prefix:null,transform:D,symbol:!1,mask:{iconName:null,prefix:null,rest:[]},maskId:null,extra:{classes:[],styles:{},attributes:{}}}}function Hn(e){var a=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{styleParser:!0},t=vs(e),n=t.iconName,r=t.prefix,i=t.rest,o=ys(e),s=vt("parseNodeAttributes",{},e),l=a.styleParser?gs(e):[];return f({iconName:n,prefix:r,transform:D,mask:{iconName:null,prefix:null,rest:[]},maskId:null,symbol:!1,extra:{classes:i,styles:l,attributes:o}},s)}var Ss=_.styles;function Ja(e){var a=m.autoReplaceSvg==="nest"?Hn(e,{styleParser:!1}):Hn(e);return~a.extra.classes.indexOf(Ma)?U("generateLayersText",e,a):U("generateSvgReplacementMutation",e,a)}function ws(){return[].concat(O(wa),O(Ea))}function Un(e){var a=arguments.length>1&&arguments[1]!==void 0?arguments[1]:null;if(!L)return Promise.resolve();var t=v.documentElement.classList,n=function(d){return t.add("".concat(Cn,"-").concat(d))},r=function(d){return t.remove("".concat(Cn,"-").concat(d))},i=m.autoFetchSvg?ws():na.concat(Object.keys(Ss));i.includes("fa")||i.push("fa");var o=[".".concat(Ma,":not([").concat(Y,"])")].concat(i.map(function(u){return".".concat(u,":not([").concat(Y,"])")})).join(", ");if(o.length===0)return Promise.resolve();var s=[];try{s=Q(e.querySelectorAll(o))}catch{}if(s.length>0)n("pending"),r("complete");else return Promise.resolve();var l=Nt.begin("onTree"),c=s.reduce(function(u,d){try{var g=Ja(d);g&&u.push(g)}catch(p){ka||p.name==="MissingIcon"&&console.error(p)}return u},[]);return new Promise(function(u,d){Promise.all(c).then(function(g){Xa(g,function(){n("active"),n("complete"),r("pending"),typeof a=="function"&&a(),l(),u()})}).catch(function(g){l(),d(g)})})}function Es(e){var a=arguments.length>1&&arguments[1]!==void 0?arguments[1]:null;Ja(e).then(function(t){t&&Xa([t],a)})}function As(e){return function(a){var t=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},n=(a||{}).icon?a:yt(a||{}),r=t.mask;return r&&(r=(r||{}).icon?r:yt(r||{})),e(n,f(f({},t),{},{mask:r}))}}var xs=function(a){var t=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},n=t.transform,r=n===void 0?D:n,i=t.symbol,o=i===void 0?!1:i,s=t.mask,l=s===void 0?null:s,c=t.maskId,u=c===void 0?null:c,d=t.classes,g=d===void 0?[]:d,p=t.attributes,S=p===void 0?{}:p,y=t.styles,A=y===void 0?{}:y;if(a){var w=a.prefix,C=a.iconName,M=a.icon;return Fe(f({type:"icon"},a),function(){return V("beforeDOMElementCreation",{iconDefinition:a,params:t}),Pt({icons:{main:bt(M),mask:l?bt(l.icon):{found:!1,width:null,height:null,icon:{}}},prefix:w,iconName:C,transform:f(f({},D),r),symbol:o,maskId:u,extra:{attributes:S,styles:A,classes:g}})})}},Is={mixout:function(){return{icon:As(xs)}},hooks:function(){return{mutationObserverCallbacks:function(t){return t.treeCallback=Un,t.nodeCallback=Es,t}}},provides:function(a){a.i2svg=function(t){var n=t.node,r=n===void 0?v:n,i=t.callback,o=i===void 0?function(){}:i;return Un(r,o)},a.generateSvgReplacementMutation=function(t,n){var r=n.iconName,i=n.prefix,o=n.transform,s=n.symbol,l=n.mask,c=n.maskId,u=n.extra;return new Promise(function(d,g){Promise.all([St(r,i),l.iconName?St(l.iconName,l.prefix):Promise.resolve({found:!1,width:512,height:512,icon:{}})]).then(function(p){var S=De(p,2),y=S[0],A=S[1];d([t,Pt({icons:{main:y,mask:A},prefix:i,iconName:r,transform:o,symbol:s,maskId:c,extra:u,watchable:!0})])}).catch(g)})},a.generateAbstractIcon=function(t){var n=t.children,r=t.attributes,i=t.main,o=t.transform,s=t.styles,l=Pe(s);l.length>0&&(r.style=l);var c;return _t(o)&&(c=U("generateAbstractTransformGrouping",{main:i,transform:o,containerWidth:i.width,iconWidth:i.width})),n.push(c||i.icon),{children:n,attributes:r}}}},Cs={mixout:function(){return{layer:function(t){var n=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},r=n.classes,i=r===void 0?[]:r;return Fe({type:"layer"},function(){V("beforeDOMElementCreation",{assembler:t,params:n});var o=[];return t(function(s){Array.isArray(s)?s.map(function(l){o=o.concat(l.abstract)}):o=o.concat(s.abstract)}),[{tag:"span",attributes:{class:["".concat(m.cssPrefix,"-layers")].concat(O(i)).join(" ")},children:o}]})}}}},ks={mixout:function(){return{counter:function(t){var n=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},r=n.title,i=r===void 0?null:r,o=n.classes,s=o===void 0?[]:o,l=n.attributes,c=l===void 0?{}:l,u=n.styles,d=u===void 0?{}:u;return Fe({type:"counter",content:t},function(){return V("beforeDOMElementCreation",{content:t,params:n}),is({content:t.toString(),title:i,extra:{attributes:c,styles:d,classes:["".concat(m.cssPrefix,"-layers-counter")].concat(O(s))}})})}}}},Ts={mixout:function(){return{text:function(t){var n=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},r=n.transform,i=r===void 0?D:r,o=n.classes,s=o===void 0?[]:o,l=n.attributes,c=l===void 0?{}:l,u=n.styles,d=u===void 0?{}:u;return Fe({type:"text",content:t},function(){return V("beforeDOMElementCreation",{content:t,params:n}),Fn({content:t,transform:f(f({},D),i),extra:{attributes:c,styles:d,classes:["".concat(m.cssPrefix,"-layers-text")].concat(O(s))}})})}}},provides:function(a){a.generateLayersText=function(t,n){var r=n.transform,i=n.extra,o=null,s=null;if(ea){var l=parseInt(getComputedStyle(t).fontSize,10),c=t.getBoundingClientRect();o=c.width/l,s=c.height/l}return Promise.resolve([t,Fn({content:t.innerHTML,width:o,height:s,transform:r,extra:i,watchable:!0})])}}},Za=new RegExp('"',"ug"),Wn=[1105920,1112319],Bn=f(f(f(f({},{FontAwesome:{normal:"fas",400:"fas"}}),si),ho),gi),At=Object.keys(Bn).reduce(function(e,a){return e[a.toLowerCase()]=Bn[a],e},{}),Ms=Object.keys(At).reduce(function(e,a){var t=At[a];return e[a]=t[900]||O(Object.entries(t))[0][1],e},{});function _s(e){var a=e.replace(Za,"");return Ra(O(a)[0]||"")}function Os(e){var a=e.getPropertyValue("font-feature-settings").includes("ss01"),t=e.getPropertyValue("content"),n=t.replace(Za,""),r=n.codePointAt(0),i=r>=Wn[0]&&r<=Wn[1],o=n.length===2?n[0]===n[1]:!1;return i||o||a}function Ds(e,a){var t=e.replace(/^['"]|['"]$/g,"").toLowerCase(),n=parseInt(a),r=isNaN(n)?"normal":n;return(At[t]||{})[r]||Ms[t]}function Yn(e,a){var t="".concat(go).concat(a.replace(":","-"));return new Promise(function(n,r){if(e.getAttribute(t)!==null)return n();var i=Q(e.children),o=i.filter(function(Le){return Le.getAttribute(dt)===a})[0],s=$.getComputedStyle(e,a),l=s.getPropertyValue("font-family"),c=l.match(wo),u=s.getPropertyValue("font-weight"),d=s.getPropertyValue("content");if(o&&!c)return e.removeChild(o),n();if(c&&d!=="none"&&d!==""){var g=s.getPropertyValue("content"),p=Ds(l,u),S=_s(g),y=c[0].startsWith("FontAwesome"),A=Os(s),w=Dt(p,S),C=w;if(y){var M=Uo(S);M.iconName&&M.prefix&&(w=M.iconName,p=M.prefix)}if(w&&!A&&(!o||o.getAttribute(Ct)!==p||o.getAttribute(kt)!==C)){e.setAttribute(t,C),o&&e.removeChild(o);var G=bs(),P=G.extra;P.attributes[dt]=a,St(w,p).then(function(Le){var rr=Pt(f(f({},G),{},{icons:{main:Le,mask:Ba()},prefix:p,iconName:C,extra:P,watchable:!0})),je=v.createElementNS("http://www.w3.org/2000/svg","svg");a==="::before"?e.insertBefore(je,e.firstChild):e.appendChild(je),je.outerHTML=rr.map(function(ir){return he(ir)}).join(`
`),e.removeAttribute(t),n()}).catch(r)}else n()}else n()})}function Ps(e){return Promise.all([Yn(e,"::before"),Yn(e,"::after")])}function Ns(e){return e.parentNode!==document.head&&!~yo.indexOf(e.tagName.toUpperCase())&&!e.getAttribute(dt)&&(!e.parentNode||e.parentNode.tagName!=="svg")}var Rs=function(a){return!!a&&Ca.some(function(t){return a.includes(t)})},Fs=function(a){if(!a)return[];var t=new Set,n=a.split(/,(?![^()]*\))/).map(function(l){return l.trim()});n=n.flatMap(function(l){return l.includes("(")?l:l.split(",").map(function(c){return c.trim()})});var r=Ce(n),i;try{for(r.s();!(i=r.n()).done;){var o=i.value;if(Rs(o)){var s=Ca.reduce(function(l,c){return l.replace(c,"")},o);s!==""&&s!=="*"&&t.add(s)}}}catch(l){r.e(l)}finally{r.f()}return t};function Vn(e){var a=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1;if(L){var t;if(a)t=e;else if(m.searchPseudoElementsFullScan)t=e.querySelectorAll("*");else{var n=new Set,r=Ce(document.styleSheets),i;try{for(r.s();!(i=r.n()).done;){var o=i.value;try{var s=Ce(o.cssRules),l;try{for(s.s();!(l=s.n()).done;){var c=l.value,u=Fs(c.selectorText),d=Ce(u),g;try{for(d.s();!(g=d.n()).done;){var p=g.value;n.add(p)}}catch(y){d.e(y)}finally{d.f()}}}catch(y){s.e(y)}finally{s.f()}}catch(y){m.searchPseudoElementsWarnings&&console.warn("Font Awesome: cannot parse stylesheet: ".concat(o.href," (").concat(y.message,`)
If it declares any Font Awesome CSS pseudo-elements, they will not be rendered as SVG icons. Add crossorigin="anonymous" to the <link>, enable searchPseudoElementsFullScan for slower but more thorough DOM parsing, or suppress this warning by setting searchPseudoElementsWarnings to false.`))}}}catch(y){r.e(y)}finally{r.f()}if(!n.size)return;var S=Array.from(n).join(", ");try{t=e.querySelectorAll(S)}catch{}}return new Promise(function(y,A){var w=Q(t).filter(Ns).map(Ps),C=Nt.begin("searchPseudoElements");Ka(),Promise.all(w).then(function(){C(),Et(),y()}).catch(function(){C(),Et(),A()})})}}var Ls={hooks:function(){return{mutationObserverCallbacks:function(t){return t.pseudoElementsCallback=Vn,t}}},provides:function(a){a.pseudoElements2svg=function(t){var n=t.node,r=n===void 0?v:n;m.searchPseudoElements&&Vn(r)}}},Gn=!1,js={mixout:function(){return{dom:{unwatch:function(){Ka(),Gn=!0}}}},hooks:function(){return{bootstrap:function(){$n(vt("mutationObserverCallbacks",{}))},noAuto:function(){hs()},watch:function(t){var n=t.observeMutationsRoot;Gn?Et():$n(vt("mutationObserverCallbacks",{observeMutationsRoot:n}))}}}},Xn=function(a){var t={size:16,x:0,y:0,flipX:!1,flipY:!1,rotate:0};return a.toLowerCase().split(" ").reduce(function(n,r){var i=r.toLowerCase().split("-"),o=i[0],s=i.slice(1).join("-");if(o&&s==="h")return n.flipX=!0,n;if(o&&s==="v")return n.flipY=!0,n;if(s=parseFloat(s),isNaN(s))return n;switch(o){case"grow":n.size=n.size+s;break;case"shrink":n.size=n.size-s;break;case"left":n.x=n.x-s;break;case"right":n.x=n.x+s;break;case"up":n.y=n.y-s;break;case"down":n.y=n.y+s;break;case"rotate":n.rotate=n.rotate+s;break}return n},t)},zs={mixout:function(){return{parse:{transform:function(t){return Xn(t)}}}},hooks:function(){return{parseNodeAttributes:function(t,n){var r=n.getAttribute("data-fa-transform");return r&&(t.transform=Xn(r)),t}}},provides:function(a){a.generateAbstractTransformGrouping=function(t){var n=t.main,r=t.transform,i=t.containerWidth,o=t.iconWidth,s={transform:"translate(".concat(i/2," 256)")},l="translate(".concat(r.x*32,", ").concat(r.y*32,") "),c="scale(".concat(r.size/16*(r.flipX?-1:1),", ").concat(r.size/16*(r.flipY?-1:1),") "),u="rotate(".concat(r.rotate," 0 0)"),d={transform:"".concat(l," ").concat(c," ").concat(u)},g={transform:"translate(".concat(o/2*-1," -256)")},p={outer:s,inner:d,path:g};return{tag:"g",attributes:f({},p.outer),children:[{tag:"g",attributes:f({},p.inner),children:[{tag:n.icon.tag,children:n.icon.children,attributes:f(f({},n.icon.attributes),p.path)}]}]}}}},lt={x:0,y:0,width:"100%",height:"100%"};function Kn(e){var a=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!0;return e.attributes&&(e.attributes.fill||a)&&(e.attributes.fill="black"),e}function $s(e){return e.tag==="g"?e.children:[e]}var Hs={hooks:function(){return{parseNodeAttributes:function(t,n){var r=n.getAttribute("data-fa-mask"),i=r?Re(r.split(" ").map(function(o){return o.trim()})):Ba();return i.prefix||(i.prefix=H()),t.mask=i,t.maskId=n.getAttribute("data-fa-mask-id"),t}}},provides:function(a){a.generateAbstractMask=function(t){var n=t.children,r=t.attributes,i=t.main,o=t.mask,s=t.maskId,l=t.transform,c=i.width,u=i.icon,d=o.width,g=o.icon,p=Oo({transform:l,containerWidth:d,iconWidth:c}),S={tag:"rect",attributes:f(f({},lt),{},{fill:"white"})},y=u.children?{children:u.children.map(Kn)}:{},A={tag:"g",attributes:f({},p.inner),children:[Kn(f({tag:u.tag,attributes:f(f({},u.attributes),p.path)},y))]},w={tag:"g",attributes:f({},p.outer),children:[A]},C="mask-".concat(s||Mn()),M="clip-".concat(s||Mn()),G={tag:"mask",attributes:f(f({},lt),{},{id:C,maskUnits:"userSpaceOnUse",maskContentUnits:"userSpaceOnUse"}),children:[S,w]},P={tag:"defs",children:[{tag:"clipPath",attributes:{id:M},children:$s(g)},G]};return n.push(P,{tag:"rect",attributes:f({fill:"currentColor","clip-path":"url(#".concat(M,")"),mask:"url(#".concat(C,")")},lt)}),{children:n,attributes:r}}}},Us={provides:function(a){var t=!1;$.matchMedia&&(t=$.matchMedia("(prefers-reduced-motion: reduce)").matches),a.missingIconAbstract=function(){var n=[],r={fill:"currentColor"},i={attributeType:"XML",repeatCount:"indefinite",dur:"2s"};n.push({tag:"path",attributes:f(f({},r),{},{d:"M156.5,447.7l-12.6,29.5c-18.7-9.5-35.9-21.2-51.5-34.9l22.7-22.7C127.6,430.5,141.5,440,156.5,447.7z M40.6,272H8.5 c1.4,21.2,5.4,41.7,11.7,61.1L50,321.2C45.1,305.5,41.8,289,40.6,272z M40.6,240c1.4-18.8,5.2-37,11.1-54.1l-29.5-12.6 C14.7,194.3,10,216.7,8.5,240H40.6z M64.3,156.5c7.8-14.9,17.2-28.8,28.1-41.5L69.7,92.3c-13.7,15.6-25.5,32.8-34.9,51.5 L64.3,156.5z M397,419.6c-13.9,12-29.4,22.3-46.1,30.4l11.9,29.8c20.7-9.9,39.8-22.6,56.9-37.6L397,419.6z M115,92.4 c13.9-12,29.4-22.3,46.1-30.4l-11.9-29.8c-20.7,9.9-39.8,22.6-56.8,37.6L115,92.4z M447.7,355.5c-7.8,14.9-17.2,28.8-28.1,41.5 l22.7,22.7c13.7-15.6,25.5-32.9,34.9-51.5L447.7,355.5z M471.4,272c-1.4,18.8-5.2,37-11.1,54.1l29.5,12.6 c7.5-21.1,12.2-43.5,13.6-66.8H471.4z M321.2,462c-15.7,5-32.2,8.2-49.2,9.4v32.1c21.2-1.4,41.7-5.4,61.1-11.7L321.2,462z M240,471.4c-18.8-1.4-37-5.2-54.1-11.1l-12.6,29.5c21.1,7.5,43.5,12.2,66.8,13.6V471.4z M462,190.8c5,15.7,8.2,32.2,9.4,49.2h32.1 c-1.4-21.2-5.4-41.7-11.7-61.1L462,190.8z M92.4,397c-12-13.9-22.3-29.4-30.4-46.1l-29.8,11.9c9.9,20.7,22.6,39.8,37.6,56.9 L92.4,397z M272,40.6c18.8,1.4,36.9,5.2,54.1,11.1l12.6-29.5C317.7,14.7,295.3,10,272,8.5V40.6z M190.8,50 c15.7-5,32.2-8.2,49.2-9.4V8.5c-21.2,1.4-41.7,5.4-61.1,11.7L190.8,50z M442.3,92.3L419.6,115c12,13.9,22.3,29.4,30.5,46.1 l29.8-11.9C470,128.5,457.3,109.4,442.3,92.3z M397,92.4l22.7-22.7c-15.6-13.7-32.8-25.5-51.5-34.9l-12.6,29.5 C370.4,72.1,384.4,81.5,397,92.4z"})});var o=f(f({},i),{},{attributeName:"opacity"}),s={tag:"circle",attributes:f(f({},r),{},{cx:"256",cy:"364",r:"28"}),children:[]};return t||s.children.push({tag:"animate",attributes:f(f({},i),{},{attributeName:"r",values:"28;14;28;28;14;28;"})},{tag:"animate",attributes:f(f({},o),{},{values:"1;0;1;1;0;1;"})}),n.push(s),n.push({tag:"path",attributes:f(f({},r),{},{opacity:"1",d:"M263.7,312h-16c-6.6,0-12-5.4-12-12c0-71,77.4-63.9,77.4-107.8c0-20-17.8-40.2-57.4-40.2c-29.1,0-44.3,9.6-59.2,28.7 c-3.9,5-11.1,6-16.2,2.4l-13.1-9.2c-5.6-3.9-6.9-11.8-2.6-17.2c21.2-27.2,46.4-44.7,91.2-44.7c52.3,0,97.4,29.8,97.4,80.2 c0,67.6-77.4,63.5-77.4,107.8C275.7,306.6,270.3,312,263.7,312z"}),children:t?[]:[{tag:"animate",attributes:f(f({},o),{},{values:"1;0;0;0;0;1;"})}]}),t||n.push({tag:"path",attributes:f(f({},r),{},{opacity:"0",d:"M232.5,134.5l7,168c0.3,6.4,5.6,11.5,12,11.5h9c6.4,0,11.7-5.1,12-11.5l7-168c0.3-6.8-5.2-12.5-12-12.5h-23 C237.7,122,232.2,127.7,232.5,134.5z"}),children:[{tag:"animate",attributes:f(f({},o),{},{values:"0;0;1;1;0;0;"})}]}),{tag:"g",attributes:{class:"missing"},children:n}}}},Ws={hooks:function(){return{parseNodeAttributes:function(t,n){var r=n.getAttribute("data-fa-symbol"),i=r===null?!1:r===""?!0:r;return t.symbol=i,t}}}},Bs=[No,Is,Cs,ks,Ts,Ls,js,zs,Hs,Us,Ws];Zo(Bs,{mixoutsTo:T});var uf=T.noAuto,qa=T.config,df=T.library,Qa=T.dom,er=T.parse,mf=T.findIconDefinition,pf=T.toHtml,tr=T.icon,hf=T.layer,Ys=T.text,Vs=T.counter;var Gs=["*"],Xs=(()=>{class e{defaultPrefix="fas";fallbackIcon=null;fixedWidth;set autoAddCss(t){qa.autoAddCss=t,this._autoAddCss=t}get autoAddCss(){return this._autoAddCss}_autoAddCss=!0;static \u0275fac=function(n){return new(n||e)};static \u0275prov=x({token:e,factory:e.\u0275fac,providedIn:"root"})}return e})(),Ks=(()=>{class e{definitions={};addIcons(...t){for(let n of t){n.prefix in this.definitions||(this.definitions[n.prefix]={}),this.definitions[n.prefix][n.iconName]=n;for(let r of n.icon[2])typeof r=="string"&&(this.definitions[n.prefix][r]=n)}}addIconPacks(...t){for(let n of t){let r=Object.keys(n).map(i=>n[i]);this.addIcons(...r)}}getIconDefinition(t,n){return t in this.definitions&&n in this.definitions[t]?this.definitions[t][n]:null}static \u0275fac=function(n){return new(n||e)};static \u0275prov=x({token:e,factory:e.\u0275fac,providedIn:"root"})}return e})(),Js=e=>{throw new Error(`Could not find icon with iconName=${e.iconName} and prefix=${e.prefix} in the icon library.`)},Zs=()=>{throw new Error("Property `icon` is required for `fa-icon`/`fa-duotone-icon` components.")},ar=e=>e!=null&&(e===90||e===180||e===270||e==="90"||e==="180"||e==="270"),qs=e=>{let a=ar(e.rotate),t={[`fa-${e.animation}`]:e.animation!=null&&!e.animation.startsWith("spin"),"fa-spin":e.animation==="spin"||e.animation==="spin-reverse","fa-spin-pulse":e.animation==="spin-pulse"||e.animation==="spin-pulse-reverse","fa-spin-reverse":e.animation==="spin-reverse"||e.animation==="spin-pulse-reverse","fa-pulse":e.animation==="spin-pulse"||e.animation==="spin-pulse-reverse","fa-fw":e.fixedWidth,"fa-border":e.border,"fa-inverse":e.inverse,"fa-layers-counter":e.counter,"fa-flip-horizontal":e.flip==="horizontal"||e.flip==="both","fa-flip-vertical":e.flip==="vertical"||e.flip==="both",[`fa-${e.size}`]:e.size!==null,[`fa-rotate-${e.rotate}`]:a,"fa-rotate-by":e.rotate!=null&&!a,[`fa-pull-${e.pull}`]:e.pull!==null,[`fa-stack-${e.stackItemSize}`]:e.stackItemSize!=null};return Object.keys(t).map(n=>t[n]?n:null).filter(n=>n!=null)},Ft=new WeakSet,nr="fa-auto-css";function Qs(e,a){if(!a.autoAddCss||Ft.has(e))return;if(e.getElementById(nr)!=null){a.autoAddCss=!1,Ft.add(e);return}let t=e.createElement("style");t.setAttribute("type","text/css"),t.setAttribute("id",nr),t.innerHTML=Qa.css();let n=e.head.childNodes,r=null;for(let i=n.length-1;i>-1;i--){let o=n[i],s=o.nodeName.toUpperCase();["STYLE","LINK"].indexOf(s)>-1&&(r=o)}e.head.insertBefore(t,r),a.autoAddCss=!1,Ft.add(e)}var el=e=>e.prefix!==void 0&&e.iconName!==void 0,tl=(e,a)=>el(e)?e:Array.isArray(e)&&e.length===2?{prefix:e[0],iconName:e[1]}:{prefix:a,iconName:e},nl=(()=>{class e{stackItemSize=be("1x");size=be();_effect=an(()=>{if(this.size())throw new Error('fa-icon is not allowed to customize size when used inside fa-stack. Set size on the enclosing fa-stack instead: <fa-stack size="4x">...</fa-stack>.')});static \u0275fac=function(n){return new(n||e)};static \u0275dir=Zt({type:e,selectors:[["fa-icon","stackItemSize",""],["fa-duotone-icon","stackItemSize",""]],inputs:{stackItemSize:[1,"stackItemSize"],size:[1,"size"]}})}return e})(),al=(()=>{class e{size=be();classes=Ye(()=>{let t=this.size(),n=t?{[`fa-${t}`]:!0}:{};return ze(ee({},n),{"fa-stack":!0})});static \u0275fac=function(n){return new(n||e)};static \u0275cmp=Be({type:e,selectors:[["fa-stack"]],hostVars:2,hostBindings:function(n,r){n&2&&nn(r.classes())},inputs:{size:[1,"size"]},ngContentSelectors:Gs,decls:1,vars:0,template:function(n,r){n&1&&(en(),tn(0))},encapsulation:2,changeDetection:0})}return e})(),kf=(()=>{class e{icon=I();title=I();animation=I();mask=I();flip=I();size=I();pull=I();border=I();inverse=I();symbol=I();rotate=I();fixedWidth=I();transform=I();a11yRole=I();renderedIconHTML=Ye(()=>{let t=this.icon()??this.config.fallbackIcon;if(!t)return Zs(),"";let n=this.findIconDefinition(t);if(!n)return"";let r=this.buildParams();Qs(this.document,this.config);let i=tr(n,r);return this.sanitizer.bypassSecurityTrustHtml(i.html.join(`
`))});document=j(k);sanitizer=j(tt);config=j(Xs);iconLibrary=j(Ks);stackItem=j(nl,{optional:!0});stack=j(al,{optional:!0});constructor(){this.stack!=null&&this.stackItem==null&&console.error('FontAwesome: fa-icon and fa-duotone-icon elements must specify stackItemSize attribute when wrapped into fa-stack. Example: <fa-icon stackItemSize="2x" />.')}findIconDefinition(t){let n=tl(t,this.config.defaultPrefix);if("icon"in n)return n;let r=this.iconLibrary.getIconDefinition(n.prefix,n.iconName);return r??(Js(n),null)}buildParams(){let t=this.fixedWidth(),n={flip:this.flip(),animation:this.animation(),border:this.border(),inverse:this.inverse(),size:this.size(),pull:this.pull(),rotate:this.rotate(),fixedWidth:typeof t=="boolean"?t:this.config.fixedWidth,stackItemSize:this.stackItem!=null?this.stackItem.stackItemSize():void 0},r=this.transform(),i=typeof r=="string"?er.transform(r):r,o=this.mask(),s=o!=null?this.findIconDefinition(o):null,l={},c=this.a11yRole();c!=null&&(l.role=c);let u={};return n.rotate!=null&&!ar(n.rotate)&&(u["--fa-rotate-angle"]=`${n.rotate}`),{title:this.title(),transform:i,classes:qs(n),mask:s??void 0,symbol:this.symbol(),attributes:l,styles:u}}static \u0275fac=function(n){return new(n||e)};static \u0275cmp=Be({type:e,selectors:[["fa-icon"]],hostAttrs:[1,"ng-fa-icon"],hostVars:2,hostBindings:function(n,r){n&2&&(Qt("innerHTML",r.renderedIconHTML(),Gt),qt("title",r.title()??void 0))},inputs:{icon:[1,"icon"],title:[1,"title"],animation:[1,"animation"],mask:[1,"mask"],flip:[1,"flip"],size:[1,"size"],pull:[1,"pull"],border:[1,"border"],inverse:[1,"inverse"],symbol:[1,"symbol"],rotate:[1,"rotate"],fixedWidth:[1,"fixedWidth"],transform:[1,"transform"],a11yRole:[1,"a11yRole"]},outputs:{icon:"iconChange",title:"titleChange",animation:"animationChange",mask:"maskChange",flip:"flipChange",size:"sizeChange",pull:"pullChange",border:"borderChange",inverse:"inverseChange",symbol:"symbolChange",rotate:"rotateChange",fixedWidth:"fixedWidthChange",transform:"transformChange",a11yRole:"a11yRoleChange"},decls:0,vars:0,template:function(n,r){},encapsulation:2,changeDetection:0})}return e})();var Tf=(()=>{class e{static \u0275fac=function(n){return new(n||e)};static \u0275mod=ye({type:e});static \u0275inj=ge({})}return e})();export{et as a,br as b,ef as c,tt as d,Ks as e,kf as f,Tf as g};
