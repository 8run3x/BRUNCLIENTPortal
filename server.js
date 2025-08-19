const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');
const querystring = require('querystring');
const crypto = require('crypto');

// Simple in-memory user store
const users = {
  admin: { password: 'admin123', role: 'admin' },
  worker: { password: 'worker123', role: 'worker' },
  client: { password: 'client123', role: 'client' }
};

const sessions = {}; // sessionId -> { username, role }

function getTranslations(lang) {
  const file = path.join(__dirname, 'locales', `${lang}.json`);
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return JSON.parse(fs.readFileSync(path.join(__dirname, 'locales', 'en.json'), 'utf8'));
  }
}

function serveFile(res, filePath, contentType = 'text/html') {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end('Not found');
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(data);
    }
  });
}

function parseCookies(req) {
  const list = {};
  const rc = req.headers.cookie;
  rc && rc.split(';').forEach(cookie => {
    const parts = cookie.split('=');
    list[parts.shift().trim()] = decodeURI(parts.join('='));
  });
  return list;
}

const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const lang = parsedUrl.query.lang || 'en';
  if (req.method === 'GET') {
    const staticPath = path.join(__dirname, 'public', parsedUrl.pathname);
    if (parsedUrl.pathname !== '/' && fs.existsSync(staticPath)) {
      const ext = path.extname(staticPath);
      const types = {
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.html': 'text/html'
      };
      return serveFile(res, staticPath, types[ext] || 'application/octet-stream');
    }
  }

  if (req.method === 'GET' && parsedUrl.pathname === '/') {
    serveFile(res, path.join(__dirname, 'public', 'index.html'));
  } else if (req.method === 'GET' && parsedUrl.pathname === '/i18n') {
    const dict = getTranslations(lang);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(dict));
  } else if (req.method === 'POST' && parsedUrl.pathname === '/login') {
    let body = '';
    req.on('data', chunk => (body += chunk));
    req.on('end', () => {
      const data = querystring.parse(body);
      const user = users[data.username];
      if (user && user.password === data.password) {
        const sid = crypto.randomBytes(16).toString('hex');
        sessions[sid] = { username: data.username, role: user.role };
        res.writeHead(302, {
          'Set-Cookie': `sid=${sid}; HttpOnly`,
          Location: '/dashboard'
        });
        res.end();
      } else {
        res.writeHead(401);
        res.end('Invalid credentials');
      }
    });
  } else if (req.method === 'GET' && parsedUrl.pathname === '/dashboard') {
    const cookies = parseCookies(req);
    const session = sessions[cookies.sid];
    if (!session) {
      res.writeHead(302, { Location: '/' });
      res.end();
      return;
    }
    const dict = getTranslations(lang);
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(`<h1>${dict.dashboard}</h1><p>${dict['role_' + session.role]}</p>`);
  } else {
    res.writeHead(404);
    res.end('Not found');
  }
});

const port = 3000;
server.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});
