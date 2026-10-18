const fs = require('fs');
const path = require('path');

function loadCommands(client) {
    const commandsPath = path.join(__dirname, '..', 'commands');
    const commandFolders = fs.readdirSync(commandsPath);
    for (const folder of commandFolders) {
        const commandFiles = fs.readdirSync(path.join(commandsPath, folder)).filter(file => file.endsWith('.js'));
        for (const file of commandFiles) {
            const command = require(path.join(commandsPath, folder, file));
            if ('data' in command && 'execute' in command) {
                client.commands.set(command.data.name, command);
            }
        }
    }
}

module.exports = { loadCommands };
