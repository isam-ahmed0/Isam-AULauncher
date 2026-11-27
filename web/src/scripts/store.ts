/* Tiny observable store ----------------------------------------------------
 * No framework, no re-render: state lives in one object, subscribers re-paint
 * the handful of DOM nodes that depend on it.
 */

export interface GameState {
  installed: boolean;
  version: string;
  path: string | null;
  running: boolean;
  pid: number;
  busy: boolean;
  latest: string | null;
  update: { needed: boolean; latest: string | null };
  needs_install: boolean;
  launcher_version: string;
  active_profile: string;
}

export interface SystemRunner {
  name: string;
  path: string;
  kind: "wine" | "proton" | string;
}

export interface StoreState {
  app: {
    name: string;
    launcher_version: string;
    game_version: string;
    platform: string;
    dev: boolean;
  };
  game: GameState;
  settings: {
    theme: string;
    web_theme: string;
    ui_mode: string;
    display_backend?: string;
    auto_update: boolean;
    discord_rpc: boolean;
    create_shortcuts: boolean;
    active_profile: string;
    gpu_id?: string;
    wine_binary?: string;
    wine_prefix?: string;
    warn_plain_wine?: boolean;
  };
  home: { image: string; note: string; image_data: string | null };
  paths: {
    appdata: string;
    profiles: string;
    guis: string;
    log: string;
    default_game_dir: string;
  };
  system: {
    gpus: any[];
    gpu: string;
    wine: string;
    wines: SystemRunner[];
    runners: SystemRunner[];
    runner: string;
    runner_kind: string;
    wine_binary: string;
    prefix: string;
  };
  status: { text: string; level: string };
  progress: number | null;
  progressLabel: string;
  maximized: boolean;
  booted: boolean;
  preview: boolean;
}

const emptyGame: GameState = {
  installed: false,
  version: "Not Installed",
  path: null,
  running: false,
  pid: 0,
  busy: false,
  latest: null,
  update: { needed: false, latest: null },
  needs_install: true,
  launcher_version: "",
  active_profile: "Default",
};

export const store: StoreState = {
  app: {
    name: "CrewLauncher",
    launcher_version: "",
    game_version: "",
    platform: "linux",
    dev: false,
  },
  game: emptyGame,
  settings: {
    theme: "Forest",
    web_theme: "dark",
    ui_mode: "web",
    display_backend: "",
    auto_update: true,
    discord_rpc: true,
    create_shortcuts: true,
    active_profile: "Default",
    gpu_id: "",
    wine_binary: "",
    wine_prefix: "",
    warn_plain_wine: true,
  },
  home: { image: "", note: "", image_data: null },
  paths: { appdata: "", profiles: "", guis: "", log: "", default_game_dir: "" },
  system: {
    gpus: [], gpu: "", wine: "", wines: [], runners: [], runner: "",
    runner_kind: "", wine_binary: "", prefix: "",
  },
  status: { text: "Starting…", level: "info" },
  progress: null,
  progressLabel: "",
  maximized: false,
  booted: false,
  preview: false,
};

type Listener = () => void;
const listeners = new Set<Listener>();

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function update(patch: Partial<StoreState>): void {
  Object.assign(store, patch);
  for (const listener of [...listeners]) {
    try {
      listener();
    } catch (err) {
      console.error("[store] listener failed", err);
    }
  }
}

export function updateGame(patch: Partial<GameState>): void {
  update({ game: { ...store.game, ...patch } });
}
