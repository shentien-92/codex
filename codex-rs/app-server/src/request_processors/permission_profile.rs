use codex_app_server_protocol::JSONRPCErrorError;
use codex_core::config::Config;
use codex_core::config::PermissionProfileSnapshot;
use codex_protocol::models::ActivePermissionProfile;
use codex_protocol::models::BUILT_IN_PERMISSION_PROFILE_DANGER_FULL_ACCESS;
use codex_protocol::models::BUILT_IN_PERMISSION_PROFILE_READ_ONLY;
use codex_protocol::models::BUILT_IN_PERMISSION_PROFILE_WORKSPACE;
use codex_protocol::models::PermissionProfile;
use codex_utils_absolute_path::AbsolutePathBuf;

use super::invalid_request;

pub(super) struct AppliedPermissionProfile {
    pub(super) permission_profile: PermissionProfile,
    pub(super) active_permission_profile: Option<ActivePermissionProfile>,
    pub(super) profile_workspace_roots: Vec<AbsolutePathBuf>,
}

pub(super) fn is_builtin_permission_profile_name(profile_name: &str) -> bool {
    matches!(
        profile_name,
        BUILT_IN_PERMISSION_PROFILE_READ_ONLY
            | BUILT_IN_PERMISSION_PROFILE_WORKSPACE
            | BUILT_IN_PERMISSION_PROFILE_DANGER_FULL_ACCESS
    )
}

pub(super) fn builtin_permission_profile(profile_name: &str) -> Option<PermissionProfile> {
    match profile_name {
        BUILT_IN_PERMISSION_PROFILE_READ_ONLY => Some(PermissionProfile::read_only()),
        BUILT_IN_PERMISSION_PROFILE_WORKSPACE => Some(PermissionProfile::workspace_write()),
        BUILT_IN_PERMISSION_PROFILE_DANGER_FULL_ACCESS => Some(PermissionProfile::Disabled),
        _ => None,
    }
}

pub(super) fn apply_builtin_permission_profile_to_config(
    config: &mut Config,
    profile_name: &str,
) -> Result<AppliedPermissionProfile, JSONRPCErrorError> {
    let permission_profile = builtin_permission_profile(profile_name).ok_or_else(|| {
        invalid_request(format!(
            "permission profile `{profile_name}` requires config reload"
        ))
    })?;
    config
        .permissions
        .set_permission_profile_from_session_snapshot(PermissionProfileSnapshot::active(
            permission_profile,
            ActivePermissionProfile::new(profile_name),
        ))
        .map_err(|err| {
            invalid_request(format!(
                "permission profile `{profile_name}` is not allowed: {err}"
            ))
        })?;
    config.permissions.network = None;
    Ok(AppliedPermissionProfile {
        permission_profile: config.permissions.permission_profile().clone(),
        active_permission_profile: config.permissions.active_permission_profile(),
        profile_workspace_roots: config.permissions.profile_workspace_roots().to_vec(),
    })
}
