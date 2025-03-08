import { useEffect, useState } from 'react';
import { Box, Typography, Link } from '@mui/material';
import axios from 'axios';

const Home = (): JSX.Element => {
  const [ffmpegVersion, setFfmpegVersion] = useState<string | null>(null);

  // In a real app, these might be provided by your backend or environment
  const serviceDID = "did:web:elideus.net"; // Replace with dynamic value if available
  const appVersion = "0.0.1"; // Replace with dynamic version if available
  const hostname = "elideus.net"; // Replace with dynamic hostname if available

  useEffect(() => {
    const fetchVersion = async () => {
      try {
        const response = await axios.get("/api/ffmpeg");
        setFfmpegVersion(response.data.ffmpeg_version);
      } catch (error) {
        console.error("Error fetching ffmpeg version", error);
      }
    };
    fetchVersion();
  }, []);

  return (
    <Box
      sx={{
        height: '100vh',
        margin: 0,
        backgroundColor: '#333',
        color: '#c1c1c1',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
        p: 2,
      }}
    >
      <Typography
        variant="h1"
        sx={{ fontSize: '20vh', m: 0 }}
      >
        {"\\m/"}
      </Typography>
      <Typography sx={{ fontSize: 14, mt: 1 }}>
        {ffmpegVersion ? ffmpegVersion : 'Loading version...'}
      </Typography>
      <Typography sx={{ fontSize: 14, mt: 1 }}>
        <Link 
          href="/.well-known/did.json" 
          sx={{ color: '#c1c1c1', textDecoration: 'none' }}
        >
          at://{serviceDID}
        </Link>{' '}
        v{appVersion} running on {hostname}
      </Typography>
      <Typography sx={{ fontSize: 14, mt: 1 }}>
        GitHub:{' '}
        <Link 
          href="https://github.com/elide-us/elideus-metal" 
          target="_blank" 
          rel="noopener noreferrer" 
          sx={{ color: '#c1c1c1', textDecoration: 'none' }}
        >
          repo
        </Link>{' '}
        -{' '}
        <Link 
          href="https://github.com/elide-us/elideus-metal/actions" 
          target="_blank" 
          rel="noopener noreferrer" 
          sx={{ color: '#c1c1c1', textDecoration: 'none' }}
        >
          build
        </Link>
      </Typography>
    </Box>
  );
};

export default Home;
