import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host");
  const protocol = requestHeaders.get("x-forwarded-proto") ?? "https";
  const metadataBase = host ? new URL(`${protocol}://${host}`) : new URL("http://localhost:3000");

  return {
    metadataBase,
    title: "GuildPilot — Discord Community Operations",
    description:
      "A secure Discord bot and web control plane for community workflows, polished interactions, and decision-ready analytics.",
    applicationName: "GuildPilot",
    icons: {
      icon: "/og.png",
      shortcut: "/og.png",
    },
    openGraph: {
      title: "GuildPilot — Run your community with confidence",
      description: "Safer workflows, polished Discord interactions, and metrics that measure real value.",
      type: "website",
      images: [
        {
          url: new URL("/og.png", metadataBase).toString(),
          width: 1680,
          height: 945,
          alt: "GuildPilot — Run your community with confidence",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: "GuildPilot — Discord Community Operations",
      description: "The calm control plane for serious Discord communities.",
      images: [new URL("/og.png", metadataBase).toString()],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
