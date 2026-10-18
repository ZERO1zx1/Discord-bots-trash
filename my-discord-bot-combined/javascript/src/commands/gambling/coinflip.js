const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const db = require('../../../database');
const { formatCurrency } = require('../../../utils/formatter');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('coinflip')
        .setDescription('Зоос шидэх')
        .addIntegerOption(option => option.setName('amount').setDescription('Бооцоо').setRequired(true))
        .addStringOption(option => option.setName('choice').setDescription('heads эсвэл tails').setRequired(true).addChoices(
            { name: 'heads', value: 'heads' },
            { name: 'tails', value: 'tails' }
        )),
    async execute(interaction) {
        const amount = interaction.options.getInteger('amount');
        const choice = interaction.options.getString('choice');
        if (amount <= 0) return interaction.reply({ content: '❌ Бооцоо эерэг байх ёстой.', ephemeral: true });
        const bal = db.getBalance(interaction.user.id);
        if (bal < amount) return interaction.reply({ content: '❌ Хүрэлцэхгүй байна.', ephemeral: true });
        const result = Math.random() < 0.5 ? 'heads' : 'tails';
        const win = choice === result;
        if (win) {
            db.addBalance(interaction.user.id, amount);
            const embed = new EmbedBuilder()
                .setTitle('🎉 Зоос шидэлт')
                .setDescription(`Тааж: ${choice} | Результат: ${result}`)
                .setColor('Green')
                .addFields({ name: 'Хожлоо!', value: formatCurrency(amount) });
            await interaction.reply({ embeds: [embed] });
        } else {
            db.addBalance(interaction.user.id, -amount);
            const embed = new EmbedBuilder()
                .setTitle('😢 Зоос шидэлт')
                .setDescription(`Тааж: ${choice} | Результат: ${result}`)
                .setColor('Red')
                .addFields({ name: 'Алдлаа', value: formatCurrency(-amount) });
            await interaction.reply({ embeds: [embed] });
        }
    }
};
