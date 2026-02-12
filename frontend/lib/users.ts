// Shared user database for both registration and login
// In production, this would be a real database like PostgreSQL or MongoDB
// Using a global variable to persist data across API calls
declare global {
  var __users: any[] | undefined;
}

if (!global.__users) {
  global.__users = [
    {
      id: '1',
      email: 'doctor@example.com',
      password: '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', // password
      role: 'doctor',
      name: 'Dr. Smith',
      licenseNumber: 'DOC123456',
      hospital: 'General Hospital'
    },
    {
      id: '2',
      email: 'patient@example.com',
      password: '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', // password
      role: 'patient',
      name: 'John Doe',
      phone: '+1234567890'
    }
  ];
}

export const users = global.__users;
