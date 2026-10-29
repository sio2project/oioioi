import logging

from django.db.models import prefetch_related_objects

logger = logging.getLogger(__name__)


def _get_subobject(obj, attr_keys):
    for attrname in attr_keys:
        obj = getattr(obj, attrname, None)
    return obj


# The following two functions can be used as a replacement for prefetch_related (or select_related)
# when the related objects are already known, for example for rounds = Round.objects.filter(contest=c)
# a .prefetch_related("contest") call can be replaced with rounds = annotate_known_related(rounds, "contest", c).
# Similiarly, for problems = ProblemInstance.objects.filter(round__in=rounds),
# problems = annotate_known_related_many(problems, "round", rounds) may be used.
# In addition to skipping redundant queries (or JOINs in case of .select_related),
# these utilities have the notable benefit of utilizing already prefetched transitively
# related objects, e.g. when annotating a ProblemInstance, its related round, problem and contest
# will be annotated too, provided that it was prefetched earlier.
#
# These functions expect iterables of objects (possibly querysets), but return lists of objects,
# so no queryset operations are possible on them. Therefore they are like `prefetch_related_objects`.
#
# If all objects are related to one other object, then annotate_known_related can be used.
# Otherwise annotate_known_related_many must be used with a list of the possible related objects.
#
# Complex/deeply related objects are supported, so it is possible for it to annotate e.g.
# "submission_report__submission__problem_instance" (given as the related_name argument).


def annotate_known_related(objs, related_name, related_obj):
    objs = list(objs)
    related_name_parts = related_name.split("__")
    attrname = related_name_parts[-1]
    id_attrname = attrname + "_id"
    subobjs_with_missing_related = []
    # Handle related None.
    related_obj_id = getattr(related_obj, "id", None)

    for obj in objs:
        subobj = _get_subobject(obj, related_name_parts[:-1])
        if subobj is None:
            continue
        if getattr(subobj, id_attrname) == related_obj_id:
            setattr(subobj, attrname, related_obj)
        else:
            subobjs_with_missing_related.append(subobj)

    if subobjs_with_missing_related:
        subobjs_logged = subobjs_with_missing_related[:3]
        subobjs_logged_ids = [getattr(subobj, id_attrname) for subobj in subobjs_logged]
        logger.warning(
            f"annotate_known_related for {related_name} relation called with (partially) missing "
            f"related_obj. Object type is {str(type(objs[0]))}. Some of the subobjects with related "
            f"objects different than the expected {related_obj} (id={related_obj_id}): "
            f"{subobjs_logged}. The ids of their related objects: {subobjs_logged_ids}."
        )
        prefetch_related_objects(subobjs_with_missing_related, attrname)

    return objs


def annotate_known_related_many(objs, related_name, related_list):
    related_dict = {rel_obj.id: rel_obj for rel_obj in related_list}
    related_name_parts = related_name.split("__")
    attrname = related_name_parts[-1]

    objs = list(objs)
    subobjs_with_missing_related = []

    for obj in objs:
        subobj = _get_subobject(obj, related_name_parts[:-1])
        if subobj is None:
            continue
        related_id = getattr(subobj, attrname + "_id")
        if related_id is None:
            setattr(subobj, attrname, None)
            continue
        related_obj = related_dict.get(related_id, None)
        if related_obj is None:
            subobjs_with_missing_related.append(subobj)
        else:
            setattr(subobj, attrname, related_obj)

    if subobjs_with_missing_related:
        subobjs_logged = subobjs_with_missing_related[:3]
        subobjs_logged_ids = [getattr(subobj, attrname + "_id") for subobj in subobjs_logged]
        logger.warning(
            f"annotate_known_related_many for {related_name} relation called with an "
            f"incomplete related_list. Object type is {str(type(objs[0]))}. Some of the "
            f"subobjects with missing related objects: {subobjs_logged}. The ids of their "
            f"related objects: {subobjs_logged_ids}"
        )
        prefetch_related_objects(subobjs_with_missing_related, attrname)

    return objs
