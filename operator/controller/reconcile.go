// Package controller holds the reconciliation core (M6).
// Pure logic (no cluster calls) so it is fully unit-testable.
package controller

import "github.com/kunal1bhan/work-res/operator/api/v1alpha1"

// Actual is the observed Deployment state the reconciler sees.
type Actual struct {
	Replicas          int32
	AvailableReplicas int32
	Image             string
}

// Action is a single remediation step the reconciler wants applied.
type Action struct {
	Kind    string // "scale" | "set-image" | "rollback"
	Image   string
	Replica int32
	Reason  string
}

// Reconcile compares desired (spec + status memory) with actual and returns
// the ordered actions plus the next status. Rules:
//  1. Image drift (actual != spec, and not mid-rollback) -> set-image.
//  2. Failed rollout (available < desired while image == spec) with
//     RollbackOnError and a known-good ReadyImage -> rollback once.
//  3. Replica drift -> scale.
func Reconcile(svc v1alpha1.ProductionService, act Actual) ([]Action, v1alpha1.ProductionServiceStatus) {
	var actions []Action
	status := svc.Status

	if act.Image != svc.Spec.Image {
		if svc.Spec.RollbackOnError && act.Image == status.ReadyImage && status.Phase == "Failed" {
			// Rollback already recorded; hold to avoid flapping.
			return actions, status
		}
		actions = append(actions, Action{Kind: "set-image", Image: svc.Spec.Image, Reason: "drift"})
		status.Phase = "Progressing"
		return actions, status
	}

	if act.AvailableReplicas < svc.Spec.Replicas {
		if svc.Spec.RollbackOnError && status.ReadyImage != "" && status.ReadyImage != svc.Spec.Image {
			actions = append(actions, Action{Kind: "rollback", Image: status.ReadyImage, Reason: "rollout-failed"})
			status.Phase = "Failed"
			return actions, status
		}
		if act.Replicas != svc.Spec.Replicas {
			actions = append(actions, Action{Kind: "scale", Replica: svc.Spec.Replicas, Reason: "replica-drift"})
		}
		status.Phase = "Progressing"
		return actions, status
	}

	status.Phase = "Ready"
	status.ReadyImage = svc.Spec.Image
	status.AvailableReplicas = act.AvailableReplicas
	return actions, status
}
