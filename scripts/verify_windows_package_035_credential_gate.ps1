# Credential Manager pertenece a la sesion real de Windows y no queda aislado
# redirigiendo LOCALAPPDATA, APPDATA ni USERPROFILE. Con la credencial presente,
# el arranque sin clave no es observable aqui.
#
# Esto NO puede abortar la verificacion. B13 declara "Windows sin clave" fuera de
# su alcance -es B14-, asi que exigir una sesion sin credencial hacia imposible
# verificar B13 en la unica maquina donde se construye: la del desarrollador, que
# usa Sirius y por tanto tiene la credencial guardada. Cada ejecucion moria en
# esta puerta despues de haber pasado ya la procedencia, el inventario y el
# aislamiento, sin que hubiera nada malo en el paquete.
#
# Lo que si hay que sostener, y se sostiene: no se manipula la credencial, no se
# compara su valor, y despues de los arranques se comprueba que su estado no ha
# cambiado. Ejecutar el paquete con la credencial presente no gasta nada: el
# arranque de Sirius construye el cliente del proveedor y no hace ninguna llamada
# -no hay ni una en la raiz de composicion-, y la prueba cierra el proceso.
Write-Step "D. Cobertura del escenario sin clave"

$CredentialAbsentBeforeLaunch = ($CredentialState -eq "ABSENT")

if ($CredentialAbsentBeforeLaunch) {
    Test-Check "La credencial de Sirius esta ausente antes de ejecutar el paquete" $true $CredentialState
}
else {
    Add-Skip "El arranque sin clave" (
        "la credencial de Sirius existe en esta sesion de Windows (estado: $CredentialState); " +
        "ese escenario es de B14 y necesita una cuenta de Windows sin la credencial: " +
        "ver docs/implementation/B13_PACKAGING.md, seccion 'Prueba de onboarding sin clave'")
    Write-Info "No se toca la credencial real: solo se consulta si existe, nunca su valor."
}
