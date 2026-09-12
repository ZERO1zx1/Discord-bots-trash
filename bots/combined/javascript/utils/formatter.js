function formatCurrency(amount) {
    return `💰 ${amount.toLocaleString()} монет`;
}

module.exports = { formatCurrency };
