# SPREEGO Expo Mobile App

This folder contains the Expo React Native version of SPREEGO. The original Vite web app remains in `frontend/`.

## Run on a physical phone with Expo Go

1. Install **Expo Go** from the Play Store/App Store.
2. Put the phone and laptop on the same Wi-Fi network.
3. Start the backend so the phone can reach it:

   ```bash
   cd backend
   uvicorn src.main:app --host 0.0.0.0 --port 8000
   ```

4. Copy `.env.example` to `.env.local` and replace the IP with the laptop's IPv4 address from `ipconfig`:

   ```env
   EXPO_PUBLIC_API_URL=http://192.168.1.15:8000
   ```

5. Start Expo:

   ```bash
   cd mobile
   npm install
   npx expo start --lan
   ```

6. Scan the terminal QR code from inside Expo Go.

If LAN mode cannot connect, try `npx expo start --tunnel`. The phone must still have internet access, and Windows Firewall may need to allow Node.js.

## Included mobile flows

- For-you feed with API fallback demo content
- Explore, Opens and Profile tabs
- Login with the existing FastAPI auth endpoint
- Secure token storage with Expo SecureStore
- Camera/library upload with Expo ImagePicker
- Direct upload and publish to the existing Spree API
- Clap interaction against the existing backend
