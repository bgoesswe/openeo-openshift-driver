from os import environ
from nameko.rpc import rpc
from nameko_sqlalchemy import DatabaseSession

from .models import Base, User
from .schema import UserSchema
from .exceptions import NotFound, LoginError
from .dependencies.crypt import CryptHandler


class AuthService:
    name = "auth"

    db = DatabaseSession(Base)
    crypt = CryptHandler()

    @rpc
    def health(self):
        return {"status": "success"}

    @rpc
    def login(self, user_id, password):
        try:
            user = self.db.query(User).filter_by(user_id=user_id).first()
            if not user or user.password != self.crypt.generate_hash(password, user.password):
                raise LoginError

            return {
                "status": "success",
                "data": {
                    "user_id": user.user_id,
                    "token": self.crypt.encode_auth_token(user.id)
                }
            }
        except LoginError:
            return {"status": "error", "exc_key":  "Forbidden"}
        except Exception:
            return {"status": "error", "exc_key":  "InternalServerError"}

    @rpc
    def identify(self, token):
        try:
            user_id = self.crypt.decode_auth_token(token)

            user = self.db.query(User).filter_by(id=user_id).first()
            if not user:
                raise LoginError

            return {
                "status": "success",
                "data": UserSchema().dump(user)
            }
        except LoginError:
            return {"status": "error", "exc_key":  "Forbidden"}
        except Exception:
            return {"status": "error", "exc_key":  "InternalServerError"}


class UsersService:
    name = "users"

    db = DatabaseSession(Base)
    crypt = CryptHandler()

    @rpc
    def health(self):
        return {"status": "success"}

    @rpc
    def create_user(self, password):
        try:
            user_id = "user-" + self.crypt.generate_random_string(8)
            project = environ.get("PROJECT")  # TODO: Implement Project Service
            sa_token = environ.get("SERVICEACCOUNT_TOKEN") # TODO: Implement Project Service
            password_hash = self.crypt.generate_hash(password)

            user = User(
                user_id=user_id,
                password=password_hash,
                project=project,
                sa_token=sa_token
            )

            self.db.add(user)
            self.db.commit()

            return {
                "status": "success",
                "data": {
                    "user_id": user.user_id
                }
            }
        except Exception:
            return {"status": "error", "exc_key":  "InternalServerError"}

    # @rpc
    # def get_user(self, id):
    #     user = self.db.query(User).get(id)

    #     if not user:
    #         raise NotFound("User with id {0} not found".format(id))

    #     return UserSchema().dump(user)

    # @rpc
    # def update_user(self, id, user_data):
    #     user = self.db.query(User).get(id)

    #     for key, value in user_data.items():
    #         if key == "password":
    #             user.password = user.generate_hash(value)
    #         else:
    #             setattr(user, key, value)

    #     self.db.commit()

    #     return UserSchema().dump(user)

    # @rpc
    # def delete_user(self, id):
    #     user = self.db.query(User).get(id)
    #     self.db.delete(user)
    #     self.db.commit()