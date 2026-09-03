const { SlashCommandBuilder, PermissionsBitField } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('clear')
        .setDescription('Мессеж цэвэрлэх')
        .addIntegerOption(opt => opt.setName('amount').setDescription('Тоо').setMinValue(1).setMaxValue(100).setRequired(true))
        .setDefaultMemberPermissions(PermissionsBitField.Flags.ManageMessages),
    async execute(interaction) {
        const amount = interaction.options.getInteger('amount');
        await interaction.reply({ content: 'Цэвэрлэж байна...', ephemeral: true });
        const deleted = await interaction.channel.bulkDelete(amount, true);
        await interaction.editReply(`🧹 ${deleted.size} мессеж цэвэрлэгдлээ.`);
    }
};
