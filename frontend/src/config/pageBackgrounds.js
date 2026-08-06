import homeBg from "../assets/backgrounds/home.jpg";
import browseBg from "../assets/backgrounds/browse.jpg";
import accountBg from "../assets/backgrounds/account.jpg";

const pageBackgrounds = [
  {
    id: "home",
    test: (pathname) => pathname === "/",
    image: homeBg,
  },
  {
    id: "account",
    test: (pathname) =>
      pathname.startsWith("/admin") ||
      pathname.startsWith("/yorumlarim") ||
      pathname.startsWith("/yorum-yap") ||
      pathname.startsWith("/profil"),
    image: accountBg,
  },
  {
    id: "browse",
    test: (pathname) =>
      pathname.startsWith("/hocalar") ||
      pathname.startsWith("/dersler") ||
      pathname.startsWith("/bolumler") ||
      pathname.startsWith("/fakulteler") ||
      pathname.startsWith("/universiteler"),
    image: browseBg,
  },
  {
    id: "default",
    test: () => true,
    image: homeBg,
  },
];

export function getPageBackground(pathname) {
  return pageBackgrounds.find((entry) => entry.test(pathname))?.image;
}

export const authBackground = accountBg;