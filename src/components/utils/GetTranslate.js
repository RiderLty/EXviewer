//using data from https://github.com/EhTagTranslation/Database
let preciseQuery = {}
console.time('getTranslate success')
fetch("./sources/translate.json").then( res=> res.json()).then( data=> {
    console.log("translate.json loaded")
    console.timeEnd('getTranslate success')
    preciseQuery = data
}).catch( err=> {
    console.log("get translate",err)
} )


export default function GetTranslate(type,value) {
    try { 
        const translated = preciseQuery[type][value]
        return translated === undefined ? value : translated 
    } catch (e) {
        return value
    }
}
export function getGuess(value,maxLength) { 
    if (value === "") return []
    const guess = []
    for (let type of Object.keys(preciseQuery)) {
        for (let name of Object.keys(preciseQuery[type])) { 
            if (preciseQuery[type][name].includes(value) || name.includes(value)) { 
                guess.push({
                    type: type,
                    origin: name,
                    translated: preciseQuery[type][name]
                })
                if (guess.length > maxLength) {
                    return guess
                }
            }
        }
    }
    return guess
}



