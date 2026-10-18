const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(path.join(__dirname, '..', 'data', 'discord.db'));

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    bank INTEGER DEFAULT 0,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    daily_last TIMESTAMP DEFAULT '1970-01-01',
    weekly_last TIMESTAMP DEFAULT '1970-01-01',
    hourly_last TIMESTAMP DEFAULT '1970-01-01',
    work_last TIMESTAMP DEFAULT '1970-01-01',
    message_count INTEGER DEFAULT 0,
    voice_seconds INTEGER DEFAULT 0,
    reaction_count INTEGER DEFAULT 0
  );
  CREATE TABLE IF NOT EXISTS battles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT,
    message_id TEXT UNIQUE,
    player1_id TEXT,
    player2_id TEXT,
    vote1 INTEGER DEFAULT 0,
    vote2 INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS battle_votes (
    battle_id INTEGER,
    voter_id TEXT,
    choice INTEGER,
    PRIMARY KEY (battle_id, voter_id)
  );
  CREATE TABLE IF NOT EXISTS shop_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    price INTEGER,
    description TEXT,
    role_id TEXT
  );
  CREATE TABLE IF NOT EXISTS user_inventory (
    user_id TEXT,
    item_id INTEGER,
    quantity INTEGER DEFAULT 1,
    PRIMARY KEY (user_id, item_id)
  );
  CREATE TABLE IF NOT EXISTS cooldowns (
    user_id TEXT,
    command TEXT,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, command)
  );
`);

function getUser(userId) {
    const row = db.prepare('SELECT * FROM users WHERE user_id = ?').get(String(userId));
    if (!row) {
        db.prepare('INSERT INTO users (user_id) VALUES (?)').run(String(userId));
        return getUser(userId);
    }
    return row;
}

function getBalance(userId) {
    return getUser(userId).balance;
}
function addBalance(userId, amount) {
    db.prepare('UPDATE users SET balance = balance + ? WHERE user_id = ?').run(amount, String(userId));
}

function getBank(userId) {
    return getUser(userId).bank;
}
function addBank(userId, amount) {
    db.prepare('UPDATE users SET bank = bank + ? WHERE user_id = ?').run(amount, String(userId));
}

function setCooldown(userId, command, timestamp) {
    db.prepare('INSERT OR REPLACE INTO cooldowns (user_id, command, last_used) VALUES (?, ?, ?)')
        .run(String(userId), command, timestamp);
}
function getCooldown(userId, command) {
    const row = db.prepare('SELECT last_used FROM cooldowns WHERE user_id = ? AND command = ?')
        .get(String(userId), command);
    return row ? row.last_used : null;
}

function addXp(userId, amount) {
    const user = getUser(userId);
    let xp = user.xp + amount;
    let level = user.level;
    const LEVEL_MULTIPLIER = 100;
    let needed = level * LEVEL_MULTIPLIER;
    let leveledUp = false;
    while (xp >= needed) {
        level++;
        xp -= needed;
        needed = level * LEVEL_MULTIPLIER;
        leveledUp = true;
    }
    db.prepare('UPDATE users SET xp = ?, level = ? WHERE user_id = ?').run(xp, level, String(userId));
    return { level, leveledUp };
}

function getRank(userId) {
    const user = getUser(userId);
    return { xp: user.xp, level: user.level };
}

// Battle functions
function createBattle(channelId, messageId, p1Id, p2Id) {
    const stmt = db.prepare('INSERT INTO battles (channel_id, message_id, player1_id, player2_id) VALUES (?, ?, ?, ?)');
    const info = stmt.run(String(channelId), String(messageId), String(p1Id), String(p2Id));
    return info.lastInsertRowid;
}
function getActiveBattle(messageId) {
    return db.prepare('SELECT id, player1_id, player2_id, status FROM battles WHERE message_id = ? AND status = ?').get(String(messageId), 'active');
}
function addVote(battleId, voterId, choice) {
    const existing = db.prepare('SELECT * FROM battle_votes WHERE battle_id = ? AND voter_id = ?').get(battleId, String(voterId));
    if (existing) return false;
    if (choice === 1) {
        db.prepare('UPDATE battles SET vote1 = vote1 + 1 WHERE id = ?').run(battleId);
    } else {
        db.prepare('UPDATE battles SET vote2 = vote2 + 1 WHERE id = ?').run(battleId);
    }
    db.prepare('INSERT INTO battle_votes (battle_id, voter_id, choice) VALUES (?, ?, ?)').run(battleId, String(voterId), choice);
    return true;
}
function finishBattle(battleId) {
    db.prepare('UPDATE battles SET status = ? WHERE id = ?').run('finished', battleId);
}

module.exports = {
    getBalance, addBalance, getBank, addBank, setCooldown, getCooldown,
    addXp, getRank, createBattle, getActiveBattle, addVote, finishBattle
};
