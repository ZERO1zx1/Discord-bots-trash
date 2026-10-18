const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const db = require('../../../database');
const { formatCurrency } = require('../../../utils/formatter');

const DAILY_BONUS = 1000;
const COOLDOWN_MS = 86400000; // 24h

function checkCooldown(last, cd) {
    if (!last) return true;
    const diff = Date.now() - new Date(last).getTime();
    return diff >= cd ? true : cd - diff;
}

module.exports = {
    data: new SlashCommandBuilder()
        .setName('daily')
        .setDescription('Өдөр тутмын урамшуулал'),
    async execute(interaction) {
        const last = db.getCooldown(interaction.user.id, 'daily');
        const ok = checkCooldown(last, COOLDOWN_MS);
        if (ok === true) {
            db.addBalance(interaction.user.id, DAILY_BONUS);
            db.setCooldown(interaction.user.id, 'daily', new Date().toISOString());
            const embed = new EmbedBuilder()
                .setTitle('🎁 Өдөр тутмын бонус')
                .setColor('Gold')
                .addFields({ name: 'Хүлээн авлаа', value: formatCurrency(DAILY_BONUS) });
            await interaction.reply({ embeds: [embed] });
        } else {
            const hours = Math.floor(ok / 3600000);
            const minutes = Math.floor((ok % 3600000) / 60000);
            await interaction.reply(`⏳ ${hours}ц ${minutes}м хүлээнэ үү.`);
        }
    }
};
