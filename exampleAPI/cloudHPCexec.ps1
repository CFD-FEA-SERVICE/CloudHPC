#Installing new script
Start-Process PowerShell -Verb RunAs -Wait -Argument "wget https://raw.githubusercontent.com/CFD-FEA-SERVICE/CloudHPC/master/exampleAPI/cloudHPCexec.ps1 -OutFile C:\Windows\System32\cloudHPCexec.ps1"

#APIKEY definition
$apikey="apikey_to_pass"

#Funzione dialogo per selezionare cartella
Function Get-Folder($initialDirectory) {
    [void] [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms')
    $FolderBrowserDialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $FolderBrowserDialog.Description = "Select a folder to be executed on the cloudHPC"
    $FolderBrowserDialog.RootFolder = 'MyComputer'
    if ($initialDirectory) { $FolderBrowserDialog.SelectedPath = $initialDirectory }
    [void] $FolderBrowserDialog.ShowDialog()
    return $FolderBrowserDialog.SelectedPath
}

#ComboBox
function Show-ComboBox {
    [CmdLetBinding()]
    Param (
        [Parameter(Mandatory=$true)] $Items,
        [Parameter(Mandatory=$false)] [switch] $ReturnIndex,
        [Parameter(Mandatory=$true)] [string] $FormTitle,
        [Parameter(Mandatory=$false)] [string] $ButtonText = "OK"
    )
    begin {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
    }
    process {
        $ComboBoxSize = New-Object System.Drawing.Size
        $ComboBoxSize.Height = 20
        $ComboBoxSize.Width = 300

        $ComboBoxPosition = New-Object -TypeName System.Drawing.Point
        $ComboBoxPosition.X = 10
        $ComboBoxPosition.Y = 10

        $ComboBox = New-Object -TypeName System.Windows.Forms.ComboBox
        $ComboBox.Location = $ComboBoxPosition
        $ComboBox.DataBindings.DefaultDataSourceUpdateMode = 0
        $ComboBox.FormattingEnabled = $true
        $ComboBox.Name = "comboBox1"
        $ComboBox.TabIndex = 0
        $ComboBox.Size = $ComboBoxSize
        
        $Items | foreach {
            $ComboBox.Items.Add($_)
            $ComboBox.SelectedIndex = 0
        } | Out-Null

        $ButtonSize = New-Object -TypeName System.Drawing.Size
        $ButtonSize.Height = 23
        $ButtonSize.Width = 60
        
        $ButtonPosition = New-Object -TypeName System.Drawing.Point
        $ButtonPosition.X = 320
        $ButtonPosition.Y = 9
        
        $ButtonOnClick = {
            $global:SelectedItem = $ComboBox.SelectedItem
            $global:SelectedIndex = $ComboBox.SelectedIndex
            $Form.Close()
        }

        $Button = New-Object -TypeName System.Windows.Forms.Button
        $Button.TabIndex = 2
        $Button.Size = $ButtonSize
        $Button.Name = "button1"
        $Button.UseVisualStyleBackColor = $true
        $Button.Text = $ButtonText
        $Button.Location = $ButtonPosition
        $Button.DataBindings.DefaultDataSourceUpdateMode = 0
        $Button.add_Click($ButtonOnClick)

        $FormSize = New-Object -TypeName System.Drawing.Size
        $FormSize.Height = 40
        $FormSize.Width = 390

        $Form = New-Object -TypeName System.Windows.Forms.Form
        $Form.AutoScaleMode = 0
        $Form.Text = $FormTitle
        $Form.Name = "form1"
        $Form.DataBindings.DefaultDataSourceUpdateMode = 0
        $Form.ClientSize = $FormSize
        $Form.FormBorderStyle = 1
        $Form.Controls.Add($Button)
        $Form.Controls.Add($ComboBox)

        $Form.ShowDialog() | Out-Null
    }
    end {
        $SelectedItem = $global:SelectedItem
        $SelectedIndex = $global:SelectedIndex
        Clear-Variable -Name "SelectedItem" -Force -Scope global
        if ($ReturnIndex) {
            return $SelectedIndex
        } else {
            return $SelectedItem
        }
    }
}
$vCPU = @("1", "2", "4", "8")
$RAM  = @("standard", "highmem", "highcpu", "highcore")

$SelectionvCPU = Show-ComboBox -Items $vCPU -FormTitle "Select n. of vCPU" -ButtonText "OK" -ReturnIndex
$SelectionRAM  = Show-ComboBox -Items $RAM  -FormTitle "Select RAM" -ButtonText "OK" -ReturnIndex

echo $vCPU[ $SelectionvCPU ]
echo $RAM[ $SelectionRAM  ]


$Folder = Get-Folder

$compress = @{
   LiteralPath     = $Folder
   DestinationPath = "$($Folder)\..\$((Get-Item $Folder).Basename)"
}

Compress-Archive @compress

Remove-Item -Path "$($Folder)\..\$((Get-Item $Folder).Basename).zip"

#Alternative WGET for windows
#(Invoke-WebRequest -Method GET -Uri https://cloud.cfdfeaservice.it/api/v1/simulation/short/6250 -H @{'api-key' = $($apikey); 'Accept' = 'application/json'}).Content

Write-Host -NoNewLine 'Press any key to continue...';
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown');
