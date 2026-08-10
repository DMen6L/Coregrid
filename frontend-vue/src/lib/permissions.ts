import type { WorkspaceRole } from "../types/api";

const MEMBERS_MANAGE_ROLES = new Set<WorkspaceRole>(["owner", "admin"]);

export function canManageMembers(role: WorkspaceRole | null | undefined) {
  return Boolean(role && MEMBERS_MANAGE_ROLES.has(role));
}

export function formatWorkspaceRole(role: string | null | undefined) {
  switch (role) {
    case "owner":
      return "Владелец";
    case "admin":
      return "Администратор";
    case "manager":
      return "Менеджер";
    case "operator":
      return "Оператор";
    case "viewer":
      return "Наблюдатель";
    default:
      return role || "Роль не указана";
  }
}
