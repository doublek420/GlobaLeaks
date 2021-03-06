/*
  This set of UT validate request/response against public resources.
*/

var request = require('supertest');

var host = 'http://127.0.0.1:8082';

var app = request(host);

var public_resources = [
  {
    'url': '/',
    'type': 'text/html',
    'status': 200
  },
  {
    'url': '/index.html',
    'type': 'text/html',
    'status': 200
  },
  {
    'url': '/public',
    'type': 'application/json',
    'status': 200
  },
  {
    'url': '/unexistent',
    'type': 'text/html; charset=UTF-8',
    'status': 404
  },
  {
    'url': '/@invalid@',
    'type': 'text/html; charset=UTF-8',
    'status': 404
  }
];

var validate_mandatory_headers = function(headers) {
  var mandatory_headers = {
    'X-XSS-Protection': '1; mode=block',
    'X-Content-Type-Options': 'nosniff',
    'Expires': '-1',
    'Server': 'globaleaks',
    'Pragma': 'no-cache',
    'Cache-control': 'no-cache, no-store, must-revalidate',
    'Referrer-Policy': 'no-referrer',
    'X-Frame-Options': 'sameorigin'
  };

  for (var key in mandatory_headers) {
    if (headers[key.toLowerCase()] !== mandatory_headers[key]) {
      throw key + ' != ' + mandatory_headers[key];
    }
  }
};

public_resources.forEach(function(req){
  describe('GET ' + req['url'], function(){
    it('responds with ' + req['type'], function(done){
      app
      .get(req['url'])
      .expect(req['status'])
      .expect('Content-Type', req['type'])
      .end(function(err, res) {
        if (err) {
          return done(err);
        } else {

          validate_mandatory_headers(res.headers);

          if (req['type'] === 'application/json') {
            // TODO JSON FORMAT VALIDATION
            // https://npmjs.org/package/jsonschema
          }
          done();
        }
      });
    });
  });
});

public_resources.forEach(function(req){
  describe('POST ' + req['url'], function(){
    it('responds with 405', function(done){
      app
      .post(req['url'])
      .expect(req['url'] == '/@invalid@' ? 404 : 405)
      .end(function(err, res) {
        if (err) {
          return done(err);
        } else {
          validate_mandatory_headers(res.headers);

          if (req['type'] === 'application/json') {
            // TODO JSON FORMAT VALIDATION
            // https://npmjs.org/package/jsonschema
          }
          done();
        }
      });
    });
  });
});

public_resources.forEach(function(req){
  describe('PUT ' + req['url'], function(){
    it('responds with 405', function(done){
      app
      .put(req['url'])
      .expect(req['url'] == '/@invalid@' ? 404 : 405)
      .end(function(err, res) {
        if (err) {
          return done(err);
        } else {
          validate_mandatory_headers(res.headers);

          if (req['type'] === 'application/json') {
            // TODO JSON FORMAT VALIDATION
            // https://npmjs.org/package/jsonschema
          }
          done();
        }
      });
    });
  });
});

public_resources.forEach(function(req){
  describe('DELETE ' + req['url'], function(){
    it('responds with ' + req['type'], function(done){
      app
      .del(req['url'])
      .expect(req['url'] == '/@invalid@' ? 404 : 405)
      .end(function(err, res) {
        if (err) {
          return done(err);
        } else {
          validate_mandatory_headers(res.headers);

          if (req['type'] === 'application/json') {
            // TODO JSON FORMAT VALIDATION
            // https://npmjs.org/package/jsonschema
          }
          done();
        }
      });
    });
  });
});
