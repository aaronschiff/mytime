from sqlalchemy import select
from sqlalchemy.orm import Session

from mytime.models import Client, Project
from mytime.services.guards import ClientHasProjectsError, can_delete_client


def list_clients(session: Session) -> list[Client]:
    return list(session.scalars(select(Client).order_by(Client.name)))


def get_client(session: Session, client_id: int) -> Client | None:
    return session.get(Client, client_id)


def create_client(session: Session, name: str) -> Client:
    client = Client(name=name.strip())
    session.add(client)
    session.commit()
    return client


def update_client(session: Session, client_id: int, name: str) -> Client | None:
    client = get_client(session, client_id)
    if client is None:
        return None
    new_name = name.strip()
    # Update all linked projects to reflect the new client name
    projects = session.scalars(
        select(Project).where(Project.client_id == client_id)
    ).all()
    for project in projects:
        project.client_name = new_name
    client.name = new_name
    session.commit()
    return client


def delete_client(session: Session, client_id: int) -> None:
    if not can_delete_client(session, client_id):
        raise ClientHasProjectsError(client_id)
    client = get_client(session, client_id)
    if client is not None:
        session.delete(client)
        session.commit()


def find_or_create(session: Session, name: str) -> Client:
    name = name.strip()
    client = session.scalars(
        select(Client).where(Client.name == name)
    ).first()
    if client is None:
        client = Client(name=name)
        session.add(client)
        session.flush()
    return client
