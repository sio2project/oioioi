Improve the OIOIOI API

Hi everyone, we are starting to work on improving the OIOIOI's API. Currently, it doesn't provide much functionality and we'd like to make it more useful.


### Endpoints

Here is the specification of endpoints we are planning on adding

### `/api/version`

Return the current version of the api.

#### Input

| parameter | type | description |
|:---------:|:----:|:-----------:|
|  n/a      |  n/a |       n/a   |

#### Output

```json
{
    "major" : {major},
    "minor" : {minor},
    "patch" : {patch}
}
```

| parameter | type | description |
|:---------:|:----:|:-----------:|
| major      |  number |       MAJOR version   |
| minor      |  number |       MINOR version   |
| patch      |  number |       PATCH version   |


### `/api/contest_list`

Return a list of contests that user is signed into.

#### Input

| arguments | description |
|:---------:|:-----------:|
| n/a       |       n/a   |

#### Output

```json

[
    {
        slug: "{contest_slug}":
        name: "{contest_name}",
    },
    ...
],

```

| parameter | type | description |
|:---------:|:----:|:-----------:|
| contest_slug      |  string | Short, unique name of the contest, typically, eg. `oi31-1` |
| contest_name      |  string | Long, unique? name of the contest, typically, eg. `XXXI Olimpiada Informatyczna` |

### `/api/user_info`

Return all available user information **unrelated** to contests.

#### Input

| parameter | type | description |
|:---------:|:----:|:-----------:|
|  n/a      |  n/a |       n/a   |

#### Output

```json
{
    "username" : {username},
    ???
}
```

| parameter | type | description |
|:---------:|:----:|:-----------:|
| username      |  string | Username of the user ;D   |

### `/api/contest/{contest_slug}/problem_list`

Return the available problems inside a contest.

#### Input

| parameter | type | description |
|:-------------:|:----:|:-----------:|
| contest_slug  |  string |  Contest slug, any returned by `/api/contest_list`.   |

#### Output

```json
{
    "{contest_slug}": {
        "{problem_slug}" : {
            "problem_name": {problem_name},
            "content_link": {
                "type": "pdf" / "other",
                "link": {link},
            }
        },
        ...
    }
}
```

| parameter | type | description |
|:---------:|:----:|:-----------:|
| contest_slug      |  string |  Contest id, any returned by `/api/contest_list`.       |
| problem_slug      |  string |  Problem id, usually a 3 letter-long short name.  |
| problem_name      |  string |    Full name of the problem   |
| link      |  string |  In case of `pdf`, a link to a PDF, else a regular link.   |

### `/api/contest/{contest_slug}/problem/{problem_slug}/`

Return ????????

#### Input

| parameter | type | description |
|:-------------:|:----:|:-----------:|
| contest_slug  |  string |  Contest slug, any returned by `/api/contest_list`.   |

#### Output

```json
{
    "{contest_slug}": {
        "{problem_slug}" : {
            "problem_name": {problem_name},
            "content_link": {
                "type": "pdf" / "other",
                "link": {link},
            }
        },
        ...
    }
}
```

| parameter | type | description |
|:---------:|:----:|:-----------:|
| contest_slug      |  string |  Contest id, any returned by `/api/contest_list`.       |
| problem_slug      |  string |  Problem id, usually a 3 letter-long short name.  |
| problem_name      |  string |    Full name of the problem   |
| link      |  string |  In case of `pdf`, a link to a PDF, else a regular link.   |

- Dla problemu:
    - Nazwa
    - Link do pdfa
    - Aktualny wynik
    - Liczba podzadań ?
    - Limity czasowe ?
    - SUBMIT
    - Lista submitów - z punktami itd...
    - Lista zgłoszeń:
        - id zgłoszenia
        - status
        - link
