"""Administrative local commands with no public registration path."""

from __future__ import annotations

import argparse
import getpass

from serviceflow.application.services import (
    CustomerService,
    RequestService,
    bootstrap_administrator,
)
from serviceflow.config import get_settings
from serviceflow.domain.enums import RequestPriority
from serviceflow.domain.errors import ServiceFlowError
from serviceflow.infrastructure.database import build_engine, build_session_factory
from serviceflow.infrastructure.repositories import UserRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ServiceFlow IL administration")
    commands = parser.add_subparsers(dest="command", required=True)
    create_admin = commands.add_parser("create-admin")
    create_admin.add_argument("--email", required=True)
    create_admin.add_argument("--display-name", required=True)
    seed_demo = commands.add_parser("seed-demo")
    seed_demo.add_argument("--admin-email", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = get_settings()
    if settings.database_url is None:
        raise RuntimeError("DATABASE_URL is required for administrative commands")
    session_factory = build_session_factory(build_engine(settings.database_url))
    try:
        with session_factory() as session:
            if args.command == "create-admin":
                password = getpass.getpass("Initial password (minimum 12 characters): ")
                if len(password) < 12:
                    raise ValueError("Password must contain at least 12 characters")
                user = bootstrap_administrator(
                    session,
                    email=args.email,
                    password=password,
                    display_name=args.display_name,
                )
                print(f"Administrator created: {user.email}")
            elif args.command == "seed-demo":
                admin = UserRepository(session).by_email(args.admin_email)
                if admin is None:
                    raise ValueError("Administrator email was not found")
                customer_service = CustomerService(session)
                customer = customer_service.create(
                    admin,
                    name="לקוח לדוגמה",
                    phone="050-000-0000",
                    email="demo@example.com",
                    address="תל אביב",
                    note="נתוני הדגמה מקומיים בלבד",
                )
                request = RequestService(session).create(
                    admin,
                    customer_id=customer.id,
                    title="בדיקת מערכת מיזוג",
                    description="קריאת הדגמה לסביבת הפיתוח המקומית",
                    priority=RequestPriority.NORMAL,
                    assigned_to=None,
                )
                print(f"Demo request created: #{request.request_number}")
    except (ServiceFlowError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
