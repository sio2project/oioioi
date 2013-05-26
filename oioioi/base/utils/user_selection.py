from django.db.models import Q


def get_user_q_expression(substr, user_field_name):
    substr = substr.split()

    if len(substr) > 2:
        q_dict = {
            user_field_name + '__first_name__icontains': ' '.join(substr[:-1]),
            user_field_name + '__last_name__icontains': substr[-1]
        }
        q_expression = Q(**q_dict)
    elif len(substr) == 2:
        q_dict_first_last = {
            user_field_name + '__first_name__icontains': substr[0],
            user_field_name + '__last_name__icontains': substr[1]
        }
        q_dict_two_first = {
            user_field_name + '__first_name__icontains': ' '.join(substr)
        }
        q_expression = Q(**q_dict_first_last) | Q(**q_dict_two_first)
    else:
        q_dict_username = {user_field_name + '__username__icontains': substr[0]}
        q_dict_first = {user_field_name + '__first_name__icontains': substr[0]}
        q_dict_last = {user_field_name + '__last_name__icontains': substr[0]}
        q_expression = Q(**q_dict_username) | Q(**q_dict_first) \
                       | Q(**q_dict_last)

    return q_expression
