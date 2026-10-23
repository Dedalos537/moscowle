/*
 * Puente entre un juego y la plataforma Moscowle.
 *
 * Dentro del reproductor (iframe) el juego no guarda nada por su cuenta: envía el resultado a la página que lo
 * contiene, que ya tiene la sesión del paciente y lo guarda en /api/save_game. Así funciona igual desde el dominio
 * de la API o desde el de cPanel, sin depender de cookies de terceros.
 * Abierto suelto (sin iframe), guarda directamente con la cookie de sesión, si la hay.
 *
 * Uso en un juego:
 *   MoscowleGame.start('Super RPG Bros.');
 *   MoscowleGame.finish({ accuracy: 80, avg_time: 12, kpis: { completion: 50, errors: 2, collected: 40 } });
 *
 * Los juegos no muestran KPIs ni niveles: eso lo ve solo el equipo.
 */
(function () {
  var params = new URLSearchParams(location.search);

  // Progreso por paciente: el juego guarda su avance (niveles, estrellas) en el navegador. Sin esto, en una
  // computadora compartida (la del terapeuta, o donde el admin probó el juego) un paciente veía el avance de
  // otro. Con «player» cada uno tiene su propio espacio; se instala antes de que el juego lea su avance.
  var player = params.get('player');
  if (player && window.localStorage && window.Storage) {
    try {
      var store = window.localStorage;
      var proto = window.Storage.prototype;
      var prefix = 'moscowle:p' + player + ':';
      var get = proto.getItem, set = proto.setItem, rem = proto.removeItem;
      proto.getItem = function (k) { return get.call(this, this === store ? prefix + k : k); };
      proto.setItem = function (k, v) { return set.call(this, this === store ? prefix + k : k, v); };
      proto.removeItem = function (k) { return rem.call(this, this === store ? prefix + k : k); };
    } catch (e) {
      /* sin almacenamiento el juego sigue, solo no recuerda el avance */
    }
  }
  var embedded = window.parent && window.parent !== window;
  var startedAt = Date.now();
  var gameName = params.get('title') || document.title || 'Juego';
  var sent = false;
  var collector = null;

  function post(type, payload) {
    if (!embedded) return;
    try {
      window.parent.postMessage({ source: 'moscowle-game', type: type, payload: payload || {} }, '*');
    } catch (e) {
      /* el juego sigue aunque no haya a quién avisar */
    }
  }

  function num(v) {
    return typeof v === 'number' && isFinite(v) ? v : null;
  }

  function build(result) {
    result = result || {};
    var kpis = {};
    var raw = result.kpis || {};
    ['completion', 'errors', 'collected'].forEach(function (k) {
      if (num(raw[k]) !== null) kpis[k] = Math.round(raw[k] * 100) / 100;
    });
    return {
      game_name: result.game_name || gameName,
      game_id: params.get('game_id') ? parseInt(params.get('game_id'), 10) : null,
      session_id: params.get('session_id') ? parseInt(params.get('session_id'), 10) : null,
      accuracy: num(result.accuracy) !== null ? result.accuracy : 0,
      avg_time: num(result.avg_time) !== null ? result.avg_time : 0,
      level_reached: num(result.level_reached),
      deaths: num(result.deaths),
      coins: num(result.coins),
      score: num(result.score),
      duration_s: Math.round((Date.now() - startedAt) / 1000),
      kpis: kpis,
    };
  }

  window.MoscowleGame = {
    embedded: embedded,
    params: params,

    start: function (name) {
      if (name) gameName = name;
      startedAt = Date.now();
      sent = false;
      post('started', { game_name: gameName });
    },

    /** Envía el resultado una sola vez por partida. Devuelve una promesa que se resuelve al terminar. */
    finish: function (result) {
      if (sent) return Promise.resolve(false);
      sent = true;
      var payload = build(result);
      if (embedded) {
        post('result', payload);
        return Promise.resolve(true);
      }
      return fetch('/api/save_game', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
        .then(function (r) {
          return r.ok;
        })
        .catch(function () {
          return false;
        });
    },

    /** Pide al reproductor cerrar el juego (botón «Salir» del propio juego). */
    exit: function () {
      post('exit');
    },

    /** fn() devuelve el resultado actual (o null si aún no hay nada que guardar). */
    onCollect: function (fn) {
      collector = fn;
    },
  };

  // El reproductor pide el resultado antes de cerrar el juego: así no se pierde una partida a medias.
  window.addEventListener('message', function (e) {
    if (e.source !== window.parent || !e.data || e.data.source !== 'moscowle-player' || e.data.type !== 'collect') return;
    var result = collector ? collector() : null;
    if (result && !sent) window.MoscowleGame.finish(result);
    else post('nothing', { duration_s: Math.round((Date.now() - startedAt) / 1000), sent: sent });
  });
})();
