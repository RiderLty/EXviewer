import { useMediaQuery } from "@mui/material";
import { makeStyles } from "@mui/styles";
import { useMemo } from "react";
import { useLocalStorage } from "./MyHooks";
import { useSetting, useSettingBind } from "./SettingHooks";


export const useSmallMatches = () => useMediaQuery('(min-width:560px)')

export const useBorderWidth = () => {
    const small_matches = useSmallMatches();
    return useMemo(() => small_matches ? 24 : 12, [small_matches]);
};

export const useMediumMatches = () => {
    const doubleRowWidth = useSettingBind("双列显示宽度", "840")
    return useMediaQuery(`(min-width:${Number(doubleRowWidth) - 40}px)`)
}
export const useCardDoubleRow = () => {
    const doubleRowWidth = useSettingBind("双列显示宽度", "840")
    return useMediaQuery(`(min-width:${doubleRowWidth}px)`)
}



const useBorderStyles = ({ borderWidth }) => {
    const useStyles = makeStyles((theme) => (
        {
            borderCard: {
                margin: "0 auto",
                marginTop: 40,
                marginBottom: 40,
                width: 754,
                borderRadius: 20,
                color: theme.palette.background.mainCard,
                boxShadow: theme.palette.page.shadow,
                overflow: "hidden"
            },
            matches_borderCard: {
                margin: "0 auto",
                marginBottom: 0,
                color: theme.palette.background.mainCard,
                overflow: "hidden"
            },
            elemContainer: {
                width: `calc(100% - ${borderWidth * 2}px)`,
                marginLeft: borderWidth,
                marginTop: borderWidth
            }
        }
    ))
    return useStyles();
};

export const BorderContainer = ({ children }) => {
    const break_matches = useMediumMatches();
    const borderWidth = useBorderWidth();
    const classes = useBorderStyles({ borderWidth });
    return (
        <div className={break_matches ? classes.borderCard : classes.matches_borderCard} >
            {children}
        </div>
    )
}

export const ElemContainer = ({ children }) => {
    const borderWidth = useBorderWidth();
    const classes = useBorderStyles({ borderWidth });
    return (
        <div className={classes.elemContainer}>
            {children}
        </div>
    );
};