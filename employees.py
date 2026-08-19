EMPLOYEES = [
    {"id": "1312", "first_name": "Sham", "last_name": "Suphian Kiranga", "department": "All Departments/Bahdela HQ"},
    {"id": "1294", "first_name": "Salumu", "last_name": "Omar Bakar", "department": "All Departments/Bahdela HQ"},
    {"id": "1306", "first_name": "Sabaha", "last_name": "Mohamed Bahdela", "department": "All Departments/Bahdela HQ"},
    {"id": "1291", "first_name": "Robert", "last_name": "Aron Macdonald", "department": "All Departments/Bahdela HQ"},
    {"id": "1292", "first_name": "Omari", "last_name": "Salum Furuku", "department": "All Departments/Bahdela HQ"},
    {"id": "1310", "first_name": "Naeema", "last_name": "Abdallah Bahdela", "department": "All Departments/Bahdela HQ"},
    {"id": "1304", "first_name": "Mussa", "last_name": "Rashidi Liungu", "department": "All Departments/Bahdela HQ"},
    {"id": "1301", "first_name": "Mrisho", "last_name": "Salim Mrisho", "department": "All Departments/Bahdela HQ"},
    {"id": "1311", "first_name": "Mohamedi", "last_name": "Abdulaziz Salim", "department": "All Departments/Bahdela HQ"},
    {"id": "1313", "first_name": "Mariam", "last_name": "Ally Bahadela", "department": "All Departments/Bahdela HQ"},
    {"id": "1296", "first_name": "Juma", "last_name": "Mohamed Ngota", "department": "All Departments/Bahdela HQ"},
    {"id": "1289", "first_name": "Hemed", "last_name": "Haji Mkuki", "department": "All Departments/Bahdela HQ"},
    {"id": "1297", "first_name": "Hamza", "last_name": "Salehe Mbegu", "department": "All Departments/Bahdela HQ"},
    {"id": "1307", "first_name": "Hamida", "last_name": "Yussuf Hassan", "department": "All Departments/Bahdela HQ"},
    {"id": "1308", "first_name": "Ayman", "last_name": "Abdallah Bahdela", "department": "All Departments/Bahdela HQ"},
    {"id": "1293", "first_name": "Athumani", "last_name": "Amir Madisa", "department": "All Departments/Bahdela HQ"},
    {"id": "1309", "first_name": "Ally", "last_name": "Omar Bahdela", "department": "All Departments/Bahdela HQ"},
    {"id": "1295", "first_name": "Ahmad", "last_name": "Said Kanza", "department": "All Departments/Bahdela HQ"},
    {"id": "1290", "first_name": "Adam", "last_name": "Obadia Mbena", "department": "All Departments/Bahdela HQ"},
    {"id": "1390", "first_name": "Lutifiya", "last_name": "Jumanne Mtinangi", "department": "All Departments/Bahdela HQ"},
]


def employee_label(employee: dict) -> str:
    return f"{employee['id']} — {employee['first_name']} {employee['last_name']}"
