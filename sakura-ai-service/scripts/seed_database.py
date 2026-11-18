"""
Data Seeding Script for SakuraPath
Loads scenario JSON files into the database

Purpose: Populate empty database tables with initial scenario data
Without this: Database has empty tables, app cannot function
With this: Database has data, workers can start practicing
"""

import json
import sys
import uuid
from pathlib import Path
from datetime import datetime

# Add parent directory to path (so we can import src)
sys.path.insert(0, str(Path(__file__).parent.parent))

ADMIN_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Import database and models
from src.postgres.postgres_manager import PostgresManager
from src.models.sakura_models import SakuraScenarios, SakuraCohorts, SakuraUsers
from src.enums.level_and_comp_status import LanguageLevel, UserStatus, UserType


def seed_scenarios():
    """
    Load scenario JSON files from scenarios/ into SCENARIOS table

    Why: Database needs initial scenario data to function

    Process:
        1. Find all JSON files in scenarios/
        2. Read each JSON file
        3. Create Scenario ORM object
        4. Save to database
    """
    print("\n SEEDING SCENARIOS...")

    db = PostgresManager.get_instance()
    scenarios_dir = Path(__file__).parent.parent / "scenarios"

    # Check if scenarios directory exists
    if not scenarios_dir.exists():
        print(f"Directory not found: {scenarios_dir}")
        return False

    # Get all JSON files, sorted by name
    json_files = sorted(scenarios_dir.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {scenarios_dir}")
        return False

    scenario_files = [f for f in json_files if not f.name.endswith("_dataseed.json")]

    if not scenario_files:
        print(f"No scenario JSON files found")
        return False

    # slug (from JSON) -> generated UUID, so callers know which scenario_id
    # to pass to POST /interview/start for a given scenario
    slug_to_uuid = {}

    try:
        with db.session_scope() as session:
            existing_count = session.query(SakuraScenarios).count()
            if existing_count > 0:
                print(f"{existing_count} scenarios already exist in database")
                print(f"   Skipping scenario seeding...")
                return True

            # Load each scenario
            for json_file in scenario_files:
                print(f"Loading {json_file.name}...", end=" ")

                try:
                    # Read JSON file
                    with open(json_file, encoding="utf-8") as f:
                        scenario_data = json.load(f)

                    # Handle both single scenario and array format
                    if isinstance(scenario_data, list):
                        # If it's an array, use first item
                        scenario_data = scenario_data[0] if scenario_data else {}

                    # scenario_id column is a UUID, but the JSON files use a
                    # human-readable slug (e.g. "reporting_problem_001") -- so
                    # generate a real UUID here and keep the slug->UUID mapping
                    # on the side for testing/reference.
                    slug = scenario_data.get("scenario_id")
                    generated_id = uuid.uuid4()
                    slug_to_uuid[slug] = str(generated_id)

                    # Create Scenario ORM object
                    scenario = SakuraScenarios(
                        scenario_id=generated_id,
                        name=scenario_data.get("name"),
                        description=scenario_data.get("description"),
                        level=scenario_data.get("level", "N5"),
                        job_domain=scenario_data.get("job_type", "manufacturing"),
                        scenario_tree=scenario_data.get("scenario_tree"),
                        vocabulary_list=scenario_data.get("vocabulary_list"),
                        grammar_focus=scenario_data.get("grammar_focus"),
                        cultural_notes=scenario_data.get("cultural_notes"),
                    )

                    # Add to session (not committed yet)
                    session.add(scenario)
                    print(f"✅ ({slug} -> {generated_id})")

                except json.JSONDecodeError as e:
                    print(f"JSON error: {e}")
                    return False
                except Exception as e:
                    print(f"Error: {e}")
                    return False

            print(f"\nLoaded {len(scenario_files)} scenarios successfully\n")

    except Exception as e:
        print(f"\n❌ Error seeding scenarios: {e}\n")
        return False

    if slug_to_uuid:
        map_path = Path(__file__).parent.parent / "scenario_id_map.json"
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(slug_to_uuid, f, indent=2, ensure_ascii=False)
        print(f"Scenario slug -> scenario_id (UUID) mapping written to {map_path}\n")

    return True


def seed_cohorts():
    """
    Create sample cohorts for testing

    Why: Learners need to belong to cohorts
    What: Creates 2-3 sample cohorts with admin references
    """
    print("SEEDING COHORTS...")

    db = PostgresManager.get_instance()

    cohorts_data = [
        {
            "cohort_id": uuid.uuid4(),
            "name": "Vietnam Batch 1 (Feb 2026)",
            "admin_id": ADMIN_UUID,
            "start_date": datetime(2026, 2, 1),
            "expected_end_date": datetime(2026, 5, 1),
            "targeted_job_readiness_score": 85,
        },
        {
            "cohort_id": uuid.uuid4(),
            "name": "Philippines Batch 1 (Mar 2026)",
            "admin_id": ADMIN_UUID,
            "start_date": datetime(2026, 3, 1),
            "expected_end_date": datetime(2026, 6, 1),
            "targeted_job_readiness_score": 80,
        },
    ]

    try:
        with db.session_scope() as session:
            # Check if cohorts already exist
            existing_count = session.query(SakuraCohorts).count()
            if existing_count > 0:
                print(f"{existing_count} cohorts already exist")
                print(f" Skipping cohort seeding...\n")
                return True

            # Create each cohort
            for cohort_data in cohorts_data:
                print(f"   Creating {cohort_data['name']}...", end=" ")

                cohort = SakuraCohorts(
                    cohort_id=cohort_data["cohort_id"],
                    name=cohort_data["name"],
                    admin_id=cohort_data["admin_id"],
                    start_date=cohort_data.get("start_date"),
                    expected_end_date=cohort_data.get("expected_end_date"),
                    targeted_job_readiness_score=cohort_data.get(
                        "targeted_job_readiness_score"
                    ),
                )

                session.add(cohort)
                print("✅")

            # Commit all cohorts
            session.commit()
            print(f"\n   ✅ Loaded {len(cohorts_data)} cohorts successfully\n")
            return True

    except Exception as e:
        print(f"❌ Error seeding cohorts: {e}\n")
        return False


def seed_admin_user():
    """
    Create admin user for testing

    Why: Admin users manage cohorts and scenarios
    What: Creates one admin user with credentials for testing
    """
    print("👤 SEEDING ADMIN USER...")

    db = PostgresManager.get_instance()

    admin_data = {
        "user_id": ADMIN_UUID,
        "email": "admin@sakurapath.com",
        "password_hash": "hashed_password_placeholder",
        "name": "Admin User",
        "language_level": LanguageLevel.N1,
        "user_type": UserType.ADMIN,
        "status": UserStatus.ACTIVE,
    }

    try:
        with db.session_scope() as session:
            # Check if admin already exists
            admin = (
                session.query(SakuraUsers)
                .filter(SakuraUsers.user_id == admin_data["user_id"])
                .first()
            )

            if admin:
                print(f"   ⚠️  Admin user already exists")
                print(f"   Skipping admin seeding...\n")
                return True

            # Create admin user
            print(f"   Creating {admin_data['name']}...", end=" ")

            admin = SakuraUsers(
                user_id=admin_data["user_id"],
                email=admin_data["email"],
                password_hash=admin_data["password_hash"],
                name=admin_data["name"],
                language_level=admin_data["language_level"],
                user_type=admin_data["user_type"],
                status=admin_data["status"],
            )

            session.add(admin)
            session.commit()
            print("✅")
            print(f"\n   ✅ Admin user created successfully\n")
            return True

    except Exception as e:
        print(f"Error seeding admin user: {e}\n")
        return False


def verify_seeding():
    """
    Verify that seeding was successful

    Why: Confirm data is actually in the database
    What: Query each table and print counts
    """
    print("🔍 VERIFYING SEEDED DATA...\n")

    db = PostgresManager.get_instance()

    try:
        with db.session_scope() as session:
            # Count scenarios
            scenario_count = session.query(SakuraScenarios).count()
            print(f"   📚 Scenarios: {scenario_count}")

            if scenario_count > 0:
                scenarios = session.query(SakuraScenarios).all()
                for scenario in scenarios[:5]:  # Show first 5
                    print(f"      - {scenario.name} ({scenario.level})")
                if scenario_count > 5:
                    print(f"      ... and {scenario_count - 5} more")

            # Count cohorts
            cohort_count = session.query(SakuraCohorts).count()
            print(f"\n   🏢 Cohorts: {cohort_count}")

            if cohort_count > 0:
                cohorts = session.query(SakuraCohorts).all()
                for cohort in cohorts:
                    print(f"      - {cohort.name}")

            # Count users
            user_count = session.query(SakuraUsers).count()
            print(f"\n   👤 Users: {user_count}")

            if user_count > 0:
                users = session.query(SakuraUsers).all()
                for user in users:
                    print(f"      - {user.name} ({user.user_type.value})")

            return True

    except Exception as e:
        print(f"❌ Error verifying data: {e}\n")
        return False


def main():
    """
    Main seed function
    Runs all seed operations in order
    """
    print("\n" + "=" * 60)
    print("🌱 SAKURAPATH DATABASE SEEDING")
    print("=" * 60)

    try:
        # Run seed functions
        scenario_success = seed_scenarios()
        admin_success = seed_admin_user()
        cohort_success = seed_cohorts()

        # Verify results
        if scenario_success and cohort_success and admin_success:
            verify_seeding()

            print("\n" + "=" * 60)
            print("✅ DATABASE SEEDING COMPLETE")
            print("=" * 60 + "\n")
            return True
        else:
            print("\n" + "=" * 60)
            print("⚠️  SEEDING COMPLETED WITH WARNINGS")
            print("=" * 60 + "\n")
            return False

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}\n")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
