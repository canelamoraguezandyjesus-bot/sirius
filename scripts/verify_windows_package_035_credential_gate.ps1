# Credential Manager pertenece a la sesion real de Windows y no queda aislado
# redirigiendo LOCALAPPDATA, APPDATA ni USERPROFILE. Por tanto, una credencial
# existente no puede compararse de forma segura sin volver a manejar su valor.
# B13 exige una sesion sin credencial y aborta antes de ejecutar Sirius.exe.
Write-Step "D. Precondicion obligatoria: credencial de Sirius ausente"

$CredentialAbsentBeforeLaunch = ($CredentialState -eq "ABSENT")
Test-Check "La credencial de Sirius esta ausente antes de ejecutar el paquete" (
    $CredentialAbsentBeforeLaunch) $CredentialState

if (-not $CredentialAbsentBeforeLaunch) {
    throw ("La verificacion exige una sesion de Windows sin la credencial de Sirius. " +
        "No se ejecutara codigo del paquete ni se manipulara Credential Manager.")
}
