"""
Generates a synthetic vehicle repair-history dataset and loads it into a
local SQLite database. Structured after real shop repair-ticket records
(vehicle, mileage at service, system affected, symptom, repair performed,
labor hours, cost) -- but every row here is fabricated for demo purposes,
not real customer data.

Includes a couple of "storyline" vehicles seeded with realistic cascading-
failure patterns (e.g. a worn suspension component leading to accelerated
tire wear, or a failing water pump eventually taking out a timing
component) so the failure-pattern-detection queries have real signal to
find, not just noise.
"""
import sqlite3
import random
from datetime import date, timedelta

random.seed(42)

SYSTEMS = ["Engine", "Transmission", "Suspension", "Brakes", "Electrical",
           "Cooling", "Exhaust", "Fuel", "Drivetrain", "Steering"]

SYMPTOM_BY_SYSTEM = {
    "Engine": ["rough idle", "check engine light", "loss of power", "oil leak"],
    "Transmission": ["slipping gears", "delayed engagement", "fluid leak", "grinding on shift"],
    "Suspension": ["clunking over bumps", "uneven tire wear", "pulls to one side", "excessive bounce"],
    "Brakes": ["squealing", "soft pedal", "vibration under braking", "grinding"],
    "Electrical": ["intermittent no-start", "dash warning lights", "battery drain", "flickering lights"],
    "Cooling": ["overheating", "coolant leak", "fan not engaging", "heater not working"],
    "Exhaust": ["rattling", "loud exhaust note", "check engine (O2 sensor)", "smell of exhaust in cabin"],
    "Fuel": ["hard starting", "poor fuel economy", "hesitation on acceleration", "fuel smell"],
    "Drivetrain": ["clunk on shift", "vibration at speed", "noise in turns", "leaking differential"],
    "Steering": ["hard to turn", "wandering at speed", "power steering whine", "looseness in wheel"],
}

REPAIR_BY_SYMPTOM_PREFIX = "Diagnosed and repaired: "

STORYLINE_VEHICLES = [
    {"vehicle_id": "V-C4-88", "year": 1988, "make": "Chevrolet", "model": "Corvette C4",
     "note": "Project car -- full engine replacement, transmission rebuild, fuel system overhaul"},
    {"vehicle_id": "V-3000GT-93", "year": 1993, "make": "Mitsubishi", "model": "3000GT VR-4",
     "note": "Project car -- head gasket, exhaust, front suspension rebuild"},
]


def random_date(start_days_ago=730, end_days_ago=1):
    d = date.today() - timedelta(days=random.randint(end_days_ago, start_days_ago))
    return d.isoformat()


def build_database(path: str = "shop_repairs.db", n_random_vehicles: int = 40, n_random_tickets: int = 400):
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    cur.executescript("""
    DROP TABLE IF EXISTS vehicles;
    DROP TABLE IF EXISTS repair_tickets;

    CREATE TABLE vehicles (
        vehicle_id TEXT PRIMARY KEY,
        year INTEGER,
        make TEXT,
        model TEXT,
        notes TEXT
    );

    CREATE TABLE repair_tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id TEXT,
        service_date TEXT,
        mileage INTEGER,
        system TEXT,
        symptom TEXT,
        repair_performed TEXT,
        labor_hours REAL,
        cost_usd REAL,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id)
    );
    """)

    vehicles = list(STORYLINE_VEHICLES)
    for i in range(n_random_vehicles):
        vehicles.append({
            "vehicle_id": f"V-R{i:03d}",
            "year": random.randint(2005, 2022),
            "make": random.choice(["Honda", "Toyota", "Ford", "Chevrolet", "Nissan", "Subaru"]),
            "model": random.choice(["Sedan", "SUV", "Truck", "Hatchback", "Coupe"]),
            "notes": None,
        })

    cur.executemany(
        "INSERT INTO vehicles VALUES (?, ?, ?, ?, ?)",
        [(v["vehicle_id"], v["year"], v["make"], v["model"], v.get("note") or v.get("notes"))
         for v in vehicles]
    )

    tickets = []

    # --- Storyline 1: worn suspension -> accelerated uneven tire/brake wear ---
    base_mileage = 145000
    for i, (system, symptom) in enumerate([
        ("Suspension", "clunking over bumps"),
        ("Suspension", "uneven tire wear"),
        ("Brakes", "vibration under braking"),
        ("Suspension", "pulls to one side"),
    ]):
        tickets.append(("V-C4-88", random_date(600 - i * 60, 500 - i * 60),
                         base_mileage + i * 800, system, symptom,
                         REPAIR_BY_SYMPTOM_PREFIX + f"{system.lower()} component",
                         round(random.uniform(1.5, 5.0), 1), round(random.uniform(150, 900), 2)))
    tickets.append(("V-C4-88", random_date(200, 150), base_mileage + 4000,
                     "Engine", "loss of power",
                     "Full engine replacement", 22.0, 4200.00))
    tickets.append(("V-C4-88", random_date(190, 140), base_mileage + 4050,
                     "Transmission", "slipping gears",
                     "Transmission rebuild", 14.0, 2600.00))
    tickets.append(("V-C4-88", random_date(180, 130), base_mileage + 4100,
                     "Fuel", "hard starting",
                     "Fuel system overhaul", 6.0, 950.00))

    # --- Storyline 2: cooling failure -> cascading head gasket failure ---
    base_mileage2 = 98000
    for i, (system, symptom) in enumerate([
        ("Cooling", "overheating"),
        ("Cooling", "coolant leak"),
        ("Cooling", "fan not engaging"),
    ]):
        tickets.append(("V-3000GT-93", random_date(400 - i * 40, 350 - i * 40),
                         base_mileage2 + i * 500, system, symptom,
                         REPAIR_BY_SYMPTOM_PREFIX + "cooling system component",
                         round(random.uniform(1.0, 4.0), 1), round(random.uniform(100, 500), 2)))
    tickets.append(("V-3000GT-93", random_date(220, 180), base_mileage2 + 1800,
                     "Engine", "check engine light",
                     "Head gasket replacement (twin-turbo VR-4)", 18.0, 3400.00))
    tickets.append(("V-3000GT-93", random_date(210, 170), base_mileage2 + 1850,
                     "Exhaust", "loud exhaust note",
                     "Exhaust system repair", 5.0, 700.00))
    tickets.append(("V-3000GT-93", random_date(200, 160), base_mileage2 + 1900,
                     "Suspension", "clunking over bumps",
                     "Front suspension rebuild", 9.0, 1600.00))

    # --- Random background tickets across the fleet ---
    for _ in range(n_random_tickets):
        v = random.choice(vehicles)
        system = random.choice(SYSTEMS)
        symptom = random.choice(SYMPTOM_BY_SYSTEM[system])
        tickets.append((
            v["vehicle_id"], random_date(), random.randint(10000, 180000),
            system, symptom, REPAIR_BY_SYMPTOM_PREFIX + f"{system.lower()} component",
            round(random.uniform(0.5, 6.0), 1), round(random.uniform(80, 1800), 2)
        ))

    cur.executemany(
        """INSERT INTO repair_tickets
           (vehicle_id, service_date, mileage, system, symptom, repair_performed, labor_hours, cost_usd)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        tickets
    )

    conn.commit()
    conn.close()
    print(f"Built {path}: {len(vehicles)} vehicles, {len(tickets)} repair tickets")


if __name__ == "__main__":
    build_database()
