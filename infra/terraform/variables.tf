variable "aws_region" {
  description = "AWS region for the demo deployment."
  type        = string
  default     = "ap-southeast-2"
}

variable "project_name" {
  description = "Short project name used in AWS resource names."
  type        = string
  default     = "cloudsec-copilot"
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "demo"
}

variable "vpc_cidr" {
  description = "CIDR range for the project VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "allowed_cidr_blocks" {
  description = "CIDRs allowed to reach the public load balancer."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "container_image" {
  description = "Immutable application image URI. Leave empty during ECR bootstrap."
  type        = string
  default     = ""
}

variable "desired_count" {
  description = "Number of Fargate tasks when container_image is configured."
  type        = number
  default     = 1

  validation {
    condition     = var.desired_count >= 1 && var.desired_count <= 4
    error_message = "desired_count must be between 1 and 4."
  }
}

variable "db_instance_class" {
  description = "RDS instance class for the portfolio environment."
  type        = string
  default     = "db.t4g.micro"
}

variable "certificate_arn" {
  description = "Optional ACM certificate ARN. Empty means HTTP-only demo traffic."
  type        = string
  default     = ""
}

variable "openai_api_key_secret_arn" {
  description = "Optional ARN of an existing Secrets Manager secret containing the API key."
  type        = string
  default     = ""
}

variable "openai_model" {
  description = "OpenAI model used by the optional analyst endpoint."
  type        = string
  default     = "gpt-5.6-terra"
}

variable "max_agent_steps" {
  description = "Maximum tool-use iterations for one analyst run."
  type        = number
  default     = 4

  validation {
    condition     = var.max_agent_steps >= 1 && var.max_agent_steps <= 8
    error_message = "max_agent_steps must be between 1 and 8."
  }
}

variable "protect_data" {
  description = "Enable deletion protection and a final RDS snapshot."
  type        = bool
  default     = false
}
