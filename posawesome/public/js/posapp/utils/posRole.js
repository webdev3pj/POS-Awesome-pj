export const OPERATIONAL_ROLES = [
  "cline-Sales Associate",
  "cline-Cashier",
  "cline-Picker",
  "cline-Dispatch",
  "cline-Supervisor",
];

export function isOperationalRole(role) {
  return OPERATIONAL_ROLES.includes(String(role || "").trim());
}

export function getBootRoles() {
  const roles = [];
  try {
    if (typeof frappe !== "undefined" && Array.isArray(frappe.user_roles)) {
      roles.push(...frappe.user_roles);
    }
    if (
      typeof frappe !== "undefined" &&
      frappe.boot &&
      frappe.boot.user &&
      Array.isArray(frappe.boot.user.roles)
    ) {
      roles.push(...frappe.boot.user.roles);
    }
  } catch (e) {}
  return Array.from(new Set(roles.map((r) => String(r || "").trim()).filter(Boolean)));
}

export function getAssignedOperationalRoles() {
  return getBootRoles().filter((r) => OPERATIONAL_ROLES.includes(r));
}

export function isAdminRoleTestingEnabled() {
  try {
    if (
      typeof frappe === "undefined" ||
      !frappe.session ||
      frappe.session.user !== "Administrator"
    ) {
      return false;
    }
    const boot = frappe.boot || {};
    const bootDev =
      parseInt(boot.developer_mode || 0, 10) === 1 ||
      parseInt((boot.conf && boot.conf.developer_mode) || 0, 10) === 1 ||
      parseInt((boot.sysdefaults && boot.sysdefaults.developer_mode) || 0, 10) === 1;
    const serverFlag =
      typeof localStorage !== "undefined" &&
      localStorage.getItem("posa_admin_role_testing_enabled") === "1";
    return bootDev || serverFlag;
  } catch (e) {
    return false;
  }
}

export function resolveCurrentRole(options = {}) {
  const assigned = getAssignedOperationalRoles();
  const allowAdminTesting = isAdminRoleTestingEnabled();
  const fallback = options.fallback || (allowAdminTesting ? "cline-Supervisor" : "");

  try {
    const stored = String(localStorage.getItem("pos_current_role") || "").trim();
    if (stored && OPERATIONAL_ROLES.includes(stored)) {
      if (allowAdminTesting || assigned.includes(stored)) {
        return stored;
      }
      localStorage.removeItem("pos_current_role");
    }
  } catch (e) {}

  if (assigned.length === 1) {
    try {
      localStorage.setItem("pos_current_role", assigned[0]);
    } catch (e) {}
    return assigned[0];
  }

  if (allowAdminTesting && OPERATIONAL_ROLES.includes(fallback)) {
    try {
      localStorage.setItem("pos_current_role", fallback);
    } catch (e) {}
    return fallback;
  }

  return "";
}

export function setAdminTestRole(role) {
  const normalized = String(role || "").trim();
  if (!isAdminRoleTestingEnabled() || !OPERATIONAL_ROLES.includes(normalized)) {
    return "";
  }
  try {
    localStorage.setItem("pos_current_role", normalized);
    localStorage.setItem("posa_admin_test_role", normalized);
  } catch (e) {}
  return normalized;
}
