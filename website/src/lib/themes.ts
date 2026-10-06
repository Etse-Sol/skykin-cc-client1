export type Theme = {
  id: string;
  name: string;
  note: string;
  swatches: [string, string, string];
};

export const THEME_STORAGE_KEY = "skykin-theme";
export const DEFAULT_THEME = "midnight";

export const themes: Theme[] = [
  {
    id: "midnight",
    name: "Midnight",
    note: "Dark · near-black, blue glow",
    swatches: ["#02080f", "#0080d0", "#d6e2ee"],
  },
  {
    id: "aurora",
    name: "Aurora",
    note: "Dark · vivid blue-violet-cyan mesh",
    swatches: ["#070a1c", "#7c4dff", "#00d1d6"],
  },
  {
    id: "emerald",
    name: "Emerald",
    note: "Dark · teal-green + blue",
    swatches: ["#04140f", "#10b981", "#0080d0"],
  },
  {
    id: "mono",
    name: "Mono",
    note: "Dark · high-contrast, blue actions",
    swatches: ["#000000", "#ffffff", "#0080d0"],
  },
  {
    id: "mist",
    name: "Cool Mist",
    note: "Dark · slate grey, silver surfaces",
    swatches: ["#151c24", "#8fa3b5", "#c3ccd6"],
  },
  {
    id: "paper",
    name: "Paper",
    note: "Light · warm ivory, navy ink",
    swatches: ["#f7f2e9", "#0080d0", "#1a2b22"],
  },
  {
    id: "slate",
    name: "Slate",
    note: "Light · cool neutral grey",
    swatches: ["#eceff3", "#0080d0", "#0d1b2a"],
  },
  {
    id: "light",
    name: "Light Premium",
    note: "Light · crisp ice white",
    swatches: ["#f5f9fd", "#0080d0", "#082038"],
  },
];
