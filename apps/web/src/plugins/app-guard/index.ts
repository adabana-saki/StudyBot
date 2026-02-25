import { registerPlugin } from "@capacitor/core";

import type { AppGuardPlugin } from "./definitions";

const AppGuard = registerPlugin<AppGuardPlugin>("AppGuard", {
  web: () => import("./web").then((m) => new m.AppGuardWeb()),
});

export * from "./definitions";
export { AppGuard };
