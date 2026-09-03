const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const db = require('../../../database');
const { formatCurrency } = require('../../../utils/formatter');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('balance')
        .setDescription('Үлдэгдлээ харах')
        .addUserOption(option => option.setName('user').setDescription('Хэрэглэгч')),
    async execute(interaction) {
        const target = interaction.options.getUser('user') || interaction.user;
        const bal = db.getBalance(target.id);
        const embed = new EmbedBuilder()
            .setTitle('💰 Үлдэгдэл')
            .setColor('Green')
            .addFields({ name: target.username, value: formatCurrency(bal) });
        await interaction.reply({ embeds: [embed] });
    }
};
