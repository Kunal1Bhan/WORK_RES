// Package v1alpha1 defines the ProductionService CRD types (M6).
package v1alpha1

// ProductionServiceSpec is the desired state.
type ProductionServiceSpec struct {
	Image    string `json:"image"`
	Replicas int32  `json:"replicas"`
	// RollbackOnError reverts to the previous image when the rollout fails.
	RollbackOnError bool `json:"rollbackOnError,omitempty"`
}

// ProductionServiceStatus is the observed state.
type ProductionServiceStatus struct {
	AvailableReplicas int32  `json:"availableReplicas,omitempty"`
	ReadyImage        string `json:"readyImage,omitempty"`
	Phase             string `json:"phase,omitempty"` // Progressing | Ready | Failed
}

// ProductionService is the full resource (metadata trimmed for this lab).
type ProductionService struct {
	Name   string                  `json:"name"`
	Spec   ProductionServiceSpec   `json:"spec"`
	Status ProductionServiceStatus `json:"status"`
}
