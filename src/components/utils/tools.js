const getStringHash = (string, index = 0, hash = 0) => {
    if (index >= string.length) {
        return hash & 0x7FFFFFFF;
    }
    return getStringHash(string, index + 1, (string.charCodeAt(index) + ((hash << 5) - hash)));
}

export {
    getStringHash,
}