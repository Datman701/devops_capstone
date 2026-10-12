{{/*
Expand the name of the chart.
*/}}
{{- define "clinicdesk.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name, capped at 63 characters for the DNS label limit.
*/}}
{{- define "clinicdesk.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "clinicdesk.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to every object.
*/}}
{{- define "clinicdesk.labels" -}}
helm.sh/chart: {{ include "clinicdesk.chart" . }}
{{ include "clinicdesk.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: clinicdesk
{{- end }}

{{/*
Selector labels. These must stay stable across upgrades — they are immutable on
an existing Deployment, so they deliberately exclude the image tag.
*/}}
{{- define "clinicdesk.selectorLabels" -}}
app.kubernetes.io/name: {{ include "clinicdesk.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "clinicdesk.backend.fullname" -}}
{{- printf "%s-backend" (include "clinicdesk.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "clinicdesk.frontend.fullname" -}}
{{- printf "%s-frontend" (include "clinicdesk.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "clinicdesk.postgresql.fullname" -}}
{{- printf "%s-postgres" (include "clinicdesk.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "clinicdesk.postgresql.servicename" -}}
{{- printf "%s-postgres" (include "clinicdesk.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "clinicdesk.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "clinicdesk.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}