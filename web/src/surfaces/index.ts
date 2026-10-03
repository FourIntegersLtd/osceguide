export { SurfaceShell, type SurfaceShellProps } from "@/surfaces/SurfaceShell";
export { WorkspaceSwitcher } from "@/surfaces/WorkspaceSwitcher";
export {
  ALL_SURFACES,
  SURFACE_MANIFESTS,
  ownsScreen,
  surfaceForKind,
  surfaceForWorkspace,
  surfaceManifest,
} from "@/surfaces/registry";
export {
  loadScreenComponent,
  loadScreensFor,
  screenComponent,
  screensFor,
} from "@/surfaces/screens";
export { resolveWorkspace, workspacesFor } from "@/surfaces/resolveWorkspace";
export type {
  NavContext,
  NavItem,
  ScreenMap,
  ScreenName,
  ScreenProps,
  ShellProps,
  SurfaceManifest,
} from "@/surfaces/contract";
