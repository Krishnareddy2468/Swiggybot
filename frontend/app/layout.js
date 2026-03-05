import "./globals.css";

export const metadata = {
  title: "Swiggy Order Bot | AI-Powered Food Ordering",
  description:
    "Order food from your favorite restaurants through natural conversation. Powered by AI for a seamless ordering experience via Telegram or Web.",
  keywords: [
    "food ordering",
    "AI bot",
    "Swiggy",
    "restaurant",
    "Telegram bot",
    "chat ordering",
  ],
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🍕</text></svg>" />
      </head>
      <body>{children}</body>
    </html>
  );
}
