# Get fresh token and save schema to file
$loginData = @{ username = "admin"; password = "AdminPassword123!" } | ConvertTo-Json
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -Body $loginData -ContentType "application/json"
$token = ($response.Content | ConvertFrom-Json).access_token
$headers = @{ "Authorization" = "Bearer $token"; "accept" = "application/json" }

$schemaResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/admin/entry/profile/schema/1" -Headers $headers
$schemaResponse.Content | Out-File -FilePath "schema.json" -Encoding UTF8
Write-Output "Schema saved to schema.json"