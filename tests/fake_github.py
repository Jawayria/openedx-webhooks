from __future__ import annotations

import dataclasses
import datetime
import random
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from urllib.parse import unquote

from .faker import Faker, FakerException, FakerModel, callback


class FakeGitHubException(FakerException):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors

    def as_json(self) -> Dict:
        j = {"message": str(self)}
        if self.errors:
            j["errors"] = self.errors
        return j

class DoesNotExist(FakeGitHubException):
    """A requested object does not exist."""
    status_code = 404

class ValidationError(FakeGitHubException):
    status_code = 422

    def __init__(self, message="Validation Failed", **kwargs):
        super().__init__(message=message, errors=[kwargs])


@dataclass
class User(FakerModel):
    login: str = "some-user"
    name: str = "Some User"
    type: str = "User"

    def as_json(self):
        return {
            "login": self.login,
            "name": self.name,
            "type": self.type,
            "url": f"https://api.github.com/users/{self.login}",
        }


@dataclass
class Label(FakerModel):
    name: str
    color: Optional[str] = "ededed"
    description: Optional[str] = None

    def __post_init__(self):
        if not re.fullmatch(r"[0-9a-fA-F]{6}", self.color):
            raise ValidationError(resource="Label", code="invalid", field="color")


DEFAULT_LABELS = [
    {"name": "bug", "color": "d73a4a", "description": "Something isn't working"},
    {"name": "documentation", "color": "0075ca", "description": "Improvements or additions to documentation"},
    {"name": "duplicate", "color": "cfd3d7", "description": "This issue or pull request already exists"},
    {"name": "enhancement", "color": "a2eeef", "description": "New feature or request"},
    {"name": "good first issue", "color": "7057ff", "description": "Good for newcomers"},
    {"name": "help wanted", "color": "008672", "description": "Extra attention is needed"},
    {"name": "invalid", "color": "e4e669", "description": "This doesn't seem right"},
    {"name": "question", "color": "d876e3", "description": "Further information is requested"},
    {"name": "wontfix", "color": "ffffff", "description": "This will not be worked on"},
]

@dataclass
class Comment(FakerModel):
    issue: PullRequest
    user: User
    body: str

    def as_json(self) -> Dict:
        return {
            "body": self.body,
            "user": self.user.as_json(),
        }


@dataclass
class PullRequest(FakerModel):
    repo: Repo
    number: int
    user: User
    title: str = ""
    body: str = ""
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    comments: List[Comment] = field(default_factory=list)
    labels: Set[str] = field(default_factory=set)
    state: str = "open"
    merged: bool = False

    def as_json(self) -> Dict:
        return {
            "number": self.number,
            "state": self.state,
            "merged": self.merged,
            "title": self.title,
            "user": self.user.as_json(),
            "body": self.body,
            "labels": [self.repo.get_label(l).as_json() for l in sorted(self.labels)],
            "base": self.repo.as_json(),
            "created_at": self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "html_url": f"https://github.com/{self.repo.owner}/{self.repo.repo}/pull/{self.number}",
        }

    def add_comment(self, user="someone", **kwargs) -> Comment:
        user = self.repo.github.get_user(user, create=True)
        comment = Comment(self, user, **kwargs)
        self.comments.append(comment)
        return comment


@dataclass
class Repo(FakerModel):
    github: FakeGitHub
    owner: str
    repo: str
    labels: Dict[str, Label] = field(default_factory=dict)
    pull_requests: Dict[int, PullRequest] = field(default_factory=dict)

    def as_json(self) -> Dict:
        return {
            "repo": {
                "full_name": f"{self.owner}/{self.repo}",
            },
        }

    def make_pull_request(self, user="someone", number=None, **kwargs) -> PullRequest:
        user = self.github.get_user(user, create=True)
        if number is None:
            highest = max(self.pull_requests.keys(), default=10)
            number = highest + random.randint(10, 20)
        pr = PullRequest(self, number, user, **kwargs)
        self.pull_requests[number] = pr
        return pr

    def get_pull_request(self, number: int) -> PullRequest:
        try:
            return self.pull_requests[number]
        except KeyError:
            raise DoesNotExist(f"Pull request {self.owner}/{self.repo} #{number} does not exist")

    def get_label(self, name: str) -> Label:
        try:
            return self.labels[name]
        except KeyError:
            raise DoesNotExist(f"Label {self.owner}/{self.repo} {name!r} does not exist")

    def has_label(self, name: str) -> bool:
        return name in self.labels

    def set_labels(self, data: List[Dict]) -> None:
        self.labels = {}
        for kwargs in data:
            self.add_label(**kwargs)

    def get_labels(self) -> List[Label]:
        return sorted(self.labels.values(), key=lambda l: l.name)

    def add_label(self, **kwargs) -> Label:
        label = Label(**kwargs)
        if label.name in self.labels:
            raise ValidationError(resource="Label", code="already_exists", field="name")
        self.labels[label.name] = label
        return label

    def update_label(self, name: str, **kwargs) -> Label:
        label = self.get_label(name)
        new_label = dataclasses.replace(label, **kwargs)
        self.labels[name] = new_label
        return new_label

    def delete_label(self, name: str) -> None:
        try:
            del self.labels[name]
        except KeyError:
            raise DoesNotExist(f"Label {self.owner}/{self.repo} {name!r} does not exist")


class FakeGitHub(Faker):

    def __init__(self, login: str = "some-user"):
        super().__init__(host="https://api.github.com")

        self.login = login
        self.users: Dict[str, User] = {}
        self.repos: Dict[str, Repo] = {}

    def make_user(self, login: str, **kwargs) -> User:
        u = self.users[login] = User(login, **kwargs)
        return u

    def get_user(self, login: str, create: bool = False) -> User:
        user = self.users.get(login)
        if user is None:
            if create:
                user = self.make_user(login)
            else:
                raise DoesNotExist(f"User {login!r} does not exist")
        return user

    def make_repo(self, owner: str, repo: str) -> Repo:
        r = Repo(self, owner, repo)
        r.set_labels(DEFAULT_LABELS)
        self.repos[f"{owner}/{repo}"] = r
        return r

    def get_repo(self, owner: str, repo: str) -> Repo:
        try:
            return self.repos[f"{owner}/{repo}"]
        except KeyError:
            raise DoesNotExist(f"Repo {owner}/{repo} does not exist")

    def make_pull_request(self, owner: str = "an-org", repo: str = "a-repo", **kwargs) -> PullRequest:
        """Convenience: make a repo and a pull request."""
        rep = self.make_repo(owner, repo)
        pr = rep.make_pull_request(**kwargs)
        return pr

    # Users

    @callback(r"/user")
    def _get_user(self, _match, _request, _context) -> Dict:
        return {"login": self.login}

    @callback(r"/users/(?P<login>[^/]+)")
    def _get_users(self, match, _request, _context) -> Dict:
        # https://developer.github.com/v3/users/#get-a-user
        return self.users[match["login"]].as_json()

    # Pull requests

    @callback(r"/repos/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pulls/(?P<number>\d+)")
    def _get_pulls(self, match, _request, _context) -> Dict:
        # https://developer.github.com/v3/pulls/#get-a-pull-request
        r = self.get_repo(match["owner"], match["repo"])
        pr = r.get_pull_request(int(match["number"]))
        return pr.as_json()

    @callback(r"/repos/(?P<owner>[^/]+)/(?P<repo>[^/]+)/issues/(?P<number>\d+)", "PATCH")
    def _patch_issues(self, match, request, _context) -> Dict:
        # https://developer.github.com/v3/issues/#update-an-issue
        r = self.get_repo(match["owner"], match["repo"])
        pr = r.get_pull_request(int(match["number"]))
        patch = request.json()
        if "labels" in patch:
            for label in patch["labels"]:
                if not r.has_label(label):
                    r.add_label(name=label)
            pr.labels = set(patch["labels"])
        return pr.as_json()

    # Repo labels

    @callback(r"/repos/(?P<owner>[^/]+)/(?P<repo>[^/]+)/labels(\?.*)?")
    def _get_labels(self, match, _request, _context) -> List[Dict]:
        # https://developer.github.com/v3/issues/labels/#list-labels-for-a-repository
        r = self.get_repo(match["owner"], match["repo"])
        return [label.as_json() for label in r.labels.values()]

    @callback(r"/repos/(?P<owner>[^/]+)/(?P<repo>[^/]+)/labels", "POST")
    def _post_labels(self, match, request, context):
        # https://developer.github.com/v3/issues/labels/#create-a-label
        r = self.get_repo(match["owner"], match["repo"])
        label = r.add_label(**request.json())
        context.status_code = 201
        return label.as_json()

    @callback(r"/repos/(?P<owner>[^/]+)/(?P<repo>[^/]+)/labels/(?P<name>.*)", "PATCH")
    def _patch_labels(self, match, request, _context):
        # https://developer.github.com/v3/issues/labels/#update-a-label
        r = self.get_repo(match["owner"], match["repo"])
        data = request.json()
        if "name" in data:
            data.pop("name")
        label = r.update_label(unquote(match["name"]), **data)
        return label.as_json()

    @callback(r"/repos/(?P<owner>[^/]+)/(?P<repo>[^/]+)/labels/(?P<name>.*)", "DELETE")
    def _delete_labels(self, match, _request, context):
        # https://developer.github.com/v3/issues/labels/#delete-a-label
        r = self.get_repo(match["owner"], match["repo"])
        r.delete_label(unquote(match["name"]))
        context.status_code = 204
        return {}

    # Comments

    @callback(r"/repos/(?P<owner>[^/]+)/(?P<repo>[^/]+)/issues/(?P<number>\d+)/comments(\?.*)?")
    def _get_issues_comments(self, match, _request, _context) -> List[Dict]:
        # https://developer.github.com/v3/issues/comments/#list-issue-comments
        r = self.get_repo(match["owner"], match["repo"])
        pr = r.get_pull_request(int(match["number"]))
        return [c.as_json() for c in pr.comments]

    @callback(r"/repos/(?P<owner>[^/]+)/(?P<repo>[^/]+)/issues/(?P<number>\d+)/comments", "POST")
    def _post_issues_comments(self, match, request, _context) -> Dict:
        # https://developer.github.com/v3/issues/comments/#create-an-issue-comment
        r = self.get_repo(match["owner"], match["repo"])
        pr = r.get_pull_request(int(match["number"]))
        comment = pr.add_comment(user=self.login, body=request.json()["body"])
        return comment.as_json()
