import KeyboardArrowLeftIcon from '@mui/icons-material/KeyboardArrowLeft';
import { IconButton } from '@mui/material';

export default function BackButton() {
    return <div
        style={{
            position: "fixed",
            top: 2,
            left: 2,
            zIndex: 999,
            width:0,
            height:0
        }}
    >

        <IconButton
            name='clickable'
            onClick={() => window.history.go(-1)}
            sx={{
                transition: ".2s",
                color: "button.iconFunction.main",
                opacity: 0.03,
                "&:hover": {
                    opacity: 1,
                },
            }}
            component="span"
        >
            <KeyboardArrowLeftIcon fontSize="small" />
        </IconButton>

    </div>
}