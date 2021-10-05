"""
This module contains custom filters for the terraform_infra role.
"""


def terraform_infra_expand_groups_gen(groups, groups_map):
    """
    Given a set of seed groups and map of groups to child groups, returns an iterator of
    all the groups for a host.
    """
    # Yield the seed groups first, just to be sure
    yield from groups
    # Calculate what additional groups to add based on which parent groups have one of
    # the seed groups in their child groups
    additional_groups = {
        parent_group
        for parent_group, child_groups in groups_map.items()
        if any(group in child_groups for group in groups)
    }
    if additional_groups:
        # We want this process to be recursive, i.e. for entries { d: [b, c], b: [a] }
        # then if a host is in group a to start with then it should end up in a, b, c and d
        yield from terraform_infra_expand_groups_gen(additional_groups, groups_map)


def terraform_infra_expand_groups(existing_groups, groups_map):
    """
    Returns the complete list of groups given a list of existing groups and a map
    of groups to child groups.
    """
    # The return value must be a list, but we want only the unique elements
    return list(set(terraform_infra_expand_groups_gen(existing_groups, groups_map)))


class FilterModule:
    """
    Custom filters for the terraform_infra role.
    """
    def filters(self):
        return {
            'terraform_infra_expand_groups': terraform_infra_expand_groups,
        }
