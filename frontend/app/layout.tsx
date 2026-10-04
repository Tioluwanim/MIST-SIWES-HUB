import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { SwRegister } from "@/components/SwRegister";

export const metadata: Metadata = {
  title: "MIST SIWES Hub",
  description: "SIWES training, attendance and project management for the Lagos State Ministry of Innovation, Science and Technology",
  manifest: "/manifest.json",
  icons: { icon: "/icon.svg", apple: "/icon.svg" },
  appleWebApp: { capable: true, title: "SIWES Hub", statusBarStyle: "default" },
};
export const viewport: Viewport = { themeColor: "#5A3825", width: "device-width", initialScale: 1, viewportFit: "cover" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
        <SwRegister />
      </body>
    </html>
  );
}
