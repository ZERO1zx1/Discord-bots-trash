module.exports = {
    name: 'ready',
    once: true,
    execute(client) {
        console.log(`✅ JS бот ${client.user.tag} аслаа!`);
    }
};
