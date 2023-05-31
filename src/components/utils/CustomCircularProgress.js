import Box from '@mui/material/Box';
import CircularProgress from "@mui/material/CircularProgress";
import Typography from '@mui/material/Typography';

export default function CustomCircularProgress(props) {
    return <Box sx={{ position: 'relative' }}>
        <CircularProgress
            variant="determinate"
            {...props}
            value={100}
            sx={{ ...props.sx, ...{ color: "background.mainCard" } }}
        />
        <CircularProgress
            variant="determinate"
            {...props}
            sx={{ ...props.sx, ...{ position: 'absolute', left: 0, } }}
        />
        {
            props.label && <Box
                sx={{
                    top: 0,
                    left: 0,
                    bottom: 0,
                    right: 0,
                    position: 'absolute',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                }}
            >
                <Typography variant="caption" component="div" color="text.secondary">
                    {`${Math.round(props.value)}%`}
                </Typography>
            </Box>
        }
    </Box>
}