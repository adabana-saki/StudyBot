import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.studybot.app",
  appName: "StudyBot",
  webDir: "out",
  server: {
    // 開発時: ローカルサーバーを指定して npx cap sync && npx cap run android
    // 本番時: デプロイURLに変更するか、コメントアウトして静的ファイルを使用
    url: "http://192.168.10.101:3001",
    cleartext: true,
    androidScheme: "https",
  },
  android: {
    allowMixedContent: true,
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      launchShowDuration: 2000,
      backgroundColor: "#0f1729",
      androidSplashResourceName: "splash",
      showSpinner: false,
    },
    StatusBar: {
      style: "DARK",
      backgroundColor: "#0f1729",
    },
  },
};

export default config;
