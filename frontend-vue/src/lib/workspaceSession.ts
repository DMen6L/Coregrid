import { computed, ref } from "vue";

import type { WorkspaceResponse } from "../types/api";

const ACTIVE_WORKSPACE_STORAGE_KEY = "coregrid.activeWorkspaceId";
export const WORKSPACE_SESSION_CHANGE_EVENT = "coregrid-workspace-session-change";

export const workspaces = ref<WorkspaceResponse[]>([]);
export const activeWorkspaceId = ref(readStoredWorkspaceId());
export const activeWorkspace = computed(() => (
  workspaces.value.find((workspace) => workspace.id === activeWorkspaceId.value) || null
));

export function getActiveWorkspaceId() {
  return activeWorkspaceId.value;
}

export function requireActiveWorkspaceId() {
  const workspaceId = getActiveWorkspaceId();

  if (!workspaceId) {
    throw new Error("Active workspace is required.");
  }

  return workspaceId;
}

export function setActiveWorkspaceId(workspaceId: number | null) {
  activeWorkspaceId.value = workspaceId;

  if (workspaceId) {
    localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, String(workspaceId));
  } else {
    localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  }

  window.dispatchEvent(new Event(WORKSPACE_SESSION_CHANGE_EVENT));
}

export function setWorkspaces(nextWorkspaces: WorkspaceResponse[]) {
  workspaces.value = [...nextWorkspaces];
}

export function selectInitialWorkspace(nextWorkspaces: WorkspaceResponse[]) {
  const currentWorkspaceId = getActiveWorkspaceId();
  const currentWorkspaceExists = nextWorkspaces.some(
    (workspace) => workspace.id === currentWorkspaceId,
  );

  if (currentWorkspaceExists) {
    return currentWorkspaceId;
  }

  return nextWorkspaces[0]?.id ?? null;
}

export function clearWorkspaceSession() {
  setWorkspaces([]);
  setActiveWorkspaceId(null);
}

export function syncActiveWorkspaceFromStorage() {
  activeWorkspaceId.value = readStoredWorkspaceId();
}

function readStoredWorkspaceId() {
  const storedValue = localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  const workspaceId = Number(storedValue || 0);

  return Number.isInteger(workspaceId) && workspaceId > 0 ? workspaceId : null;
}
