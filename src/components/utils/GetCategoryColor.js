import { getStringHash } from "./tools";

const colorMap = {
    "manga": "#ff9700",
    "doujinshi": "#f44236",
    "non-h": "#9c28b1",
    "cosplay": "#9c28b1",
    "image set": "#3f51b5",
    "western": "#8bc24a",
    "game cg": "#4cb050",
    "misc": "#f06292",
    "artist cg": "#9c28b1",
    "private": "#000000",
};

const MaterialColors = [
    '#F44336',
    '#E91E63',
    '#9C27B0',
    '#673AB7',
    '#3F51B5',
    '#2196F3',
    '#03A9F4',
    '#00BCD4',
    '#009688',
    '#4CAF50',
    '#8BC34A',
    '#CDDC39',
    '#FFEB3B',
    '#FFC107',
    '#FF9800',
    '#FF5722',
]



const randomColor = (str) => {
    return MaterialColors[  getStringHash(str) % MaterialColors.length ];
}

const getCategoryColor = (category_str) => {
    const lower_category = category_str.toLowerCase();
    if (lower_category in colorMap) {
        return colorMap[lower_category];
    } else {
        return randomColor(lower_category);
    }
}
export default getCategoryColor;