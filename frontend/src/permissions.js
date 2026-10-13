export const ROLE_PATHS = {
  administrator: '*',
  information_officer: ['/', '/patients', '/registration', '/admissions', '/emergency', '/wards', '/appointments', '/reports'],
  doctor: ['/', '/patients', '/admissions', '/emergency', '/wards', '/consultations', '/laboratory', '/prescriptions', '/appointments', '/online-consultation'],
  nurse: ['/', '/patients', '/admissions', '/emergency', '/wards', '/nursing', '/laboratory', '/appointments'],
  cashier: ['/', '/patients', '/billing', '/payments', '/receipts', '/reports'],
  laboratory_staff: ['/', '/laboratory'],
  pharmacy_staff: ['/', '/prescriptions', '/pharmacy', '/inventory', '/procurement'],
  patient: ['/', '/patients', '/appointments', '/online-consultation', '/billing', '/receipts'],
}

export function canAccessPath(roles = [], path) {
  return roles.some(role => {
    const allowed = ROLE_PATHS[role]
    return allowed === '*' || (Array.isArray(allowed) && allowed.includes(path))
  })
}
