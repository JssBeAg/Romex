"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Avatar from "@/components/Avatar";
import ErrorDialog from "@/components/ErrorDialog";
import { validateOnServer } from "@/lib/http";
import { MECHANIC_ROLE, OPERATOR_ROLE } from "@/lib/roles";
import { useFormFeedback } from "@/lib/useFormFeedback";
import { getMunicipalities, useStates, withCurrent } from "@/lib/locations";
import {
  type ApiResult,
  type Catalogs,
  type ContactInput,
  type FieldErrors,
  type Option,
  type Worker,
  type WorkerInput,
  getCatalogs,
  PHOTO_MAX_MB,
  PHOTO_TYPES,
  deleteWorkerPhoto,
  photoProblem,
  uploadWorkerPhoto,
} from "@/lib/workers";

// Field name (as the API names it) -> label shown in the error window
const LABELS: Record<string, string> = {
  enrollment_id: "Matrícula",
  first_name: "Nombre(s)",
  paternal_surname: "Apellido paterno",
  maternal_surname: "Apellido materno",
  email: "Correo electrónico",
  phone_code_id: "Código del país",
  phone_number: "Número telefónico",
  contacts: "Otros contactos",
  sex_id: "Sexo",
  role_id: "Rol",
  is_active: "Activo",
  state: "Estado",
  municipality: "Municipio",
  neighborhood: "Colonia",
  street: "Calle",
  exterior_number: "Número exterior",
  interior_number: "Número interior",
  password: "Contraseña",
  photo: "Fotografía",
  password_confirmation: "Confirmación de contraseña",
};

// A contact row of the form: strings for the inputs, plus a key for React
type ContactRow = {
  key: number;
  id: number | null;
  kind: "telefono" | "correo";
  phoneCodeId: string;
  value: string;
  label: string;
  contactName: string;
};

type Props = {
  worker?: Worker; // present when editing
  onSubmit: (input: WorkerInput) => Promise<ApiResult<{ worker: Worker }>>;
  onSaved: () => void;
  onCancel: () => void;
};

export default function WorkerForm({ worker, onSubmit, onSaved, onCancel }: Props) {
  const editing = worker !== undefined;

  const [enrollmentId, setEnrollmentId] = useState(worker?.enrollment_id ?? "");
  const [firstName, setFirstName] = useState(worker?.first_name ?? "");
  const [paternalSurname, setPaternalSurname] = useState(worker?.paternal_surname ?? "");
  const [maternalSurname, setMaternalSurname] = useState(worker?.maternal_surname ?? "");
  const [email, setEmail] = useState(worker?.email ?? "");
  const [phoneCodeId, setPhoneCodeId] = useState(worker?.phone_code ? String(worker.phone_code.id) : "");
  const [phoneNumber, setPhoneNumber] = useState(worker?.phone_number ?? "");
  const nextRowKey = useRef(0);
  const [contacts, setContacts] = useState<ContactRow[]>(() =>
    (worker?.contacts ?? []).map((c) => ({
      key: nextRowKey.current++,
      id: c.id,
      kind: c.kind,
      phoneCodeId: c.phone_code_id ? String(c.phone_code_id) : "",
      value: c.value,
      label: c.label,
      contactName: c.contact_name,
    }))
  );
  const [sexId, setSexId] = useState(worker ? String(worker.sex.id) : "");
  const [roleId, setRoleId] = useState(worker?.role ? String(worker.role.id) : "");
  const [isActive, setIsActive] = useState(worker?.is_active ?? true);
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [exteriorNumber, setExteriorNumber] = useState(worker?.address.exterior_number ?? "");
  const [interiorNumber, setInteriorNumber] = useState(worker?.address.interior_number ?? "");

  // State and municipality: names from INEGI's catalog (the country is always México)
  const [state, setState] = useState(worker?.address.state ?? "");
  const [municipality, setMunicipality] = useState(worker?.address.municipality ?? "");
  const [municipalityNames, setMunicipalityNames] = useState<string[]>([]);
  const [municipalitiesError, setMunicipalitiesError] = useState("");
  const { states: stateNames, error: statesError } = useStates(worker?.address.state ?? "");
  // Colonia and street are free text
  const [neighborhood, setNeighborhood] = useState(worker?.address.neighborhood ?? "");
  const [street, setStreet] = useState(worker?.address.street ?? "");
  const [catalogs, setCatalogs] = useState<Catalogs | null>(null);

  // Profile photo (optional): a file chosen but not sent yet, or the wish to remove the current one
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [removePhoto, setRemovePhoto] = useState(false);
  const [photoWarning, setPhotoWarning] = useState(""); // the worker was saved but the photo was not
  const photoInput = useRef<HTMLInputElement>(null);

  const [defaultCodeId, setDefaultCodeId] = useState("");
  const [generalError, setGeneralError] = useState(""); // the catalogs could not be loaded
  const [submitting, setSubmitting] = useState(false);

  // What the form sends. The server also checks it while it is being filled in.
  const input: WorkerInput = {
    enrollment_id: enrollmentId,
    first_name: firstName,
    paternal_surname: paternalSurname,
    maternal_surname: maternalSurname,
    email,
    phone_code_id: phoneCodeId ? Number(phoneCodeId) : null,
    phone_number: phoneNumber,
    contacts: contacts.map(
      (row): ContactInput => ({
        id: row.id,
        kind: row.kind,
        phone_code_id: row.kind === "telefono" && row.phoneCodeId ? Number(row.phoneCodeId) : null,
        value: row.value,
        label: row.label,
        contact_name: row.contactName,
      })
    ),
    sex_id: sexId ? Number(sexId) : null,
    role_id: roleId ? Number(roleId) : null,
    is_active: isActive,
    password,
    address: {
      state,
      municipality,
      neighborhood,
      street,
      exterior_number: exteriorNumber,
      interior_number: interiorNumber,
    },
  };
  const photoError = photoFile ? photoProblem(photoFile) : "";
  const localErrors: FieldErrors = {
    ...(password !== passwordConfirmation
      ? { password_confirmation: ["Las contraseñas no coinciden."] }
      : {}),
    ...(photoError ? { photo: [photoError] } : {}),
  };
  const feedback = useFormFeedback({
    payload: input,
    validate: (current) => validateOnServer("trabajadores", worker?.id ?? null, current),
    localErrors,
    labels: LABELS,
  });

  // A local address to preview the chosen photo (released when it changes)
  useEffect(() => {
    if (!photoFile || photoProblem(photoFile)) {
      setPhotoPreview(null);
      return;
    }
    const url = URL.createObjectURL(photoFile);
    setPhotoPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photoFile]);

  function choosePhoto(file: File | null) {
    setPhotoFile(file);
    if (file) setRemovePhoto(false);
  }

  function clearPhoto() {
    setPhotoFile(null);
    if (photoInput.current) photoInput.current.value = "";
    // With a saved photo, "remove" also means taking it off when the form is saved
    if (worker?.photo_url) setRemovePhoto(true);
  }

  // Load the catalogs, and (when editing) the options of every address level
  useEffect(() => {
    async function load() {
      const res = await getCatalogs();
      if (!res.ok || !res.data) {
        setGeneralError(res.error ?? "No se pudieron cargar los catálogos");
        return;
      }
      setCatalogs(res.data);
      // New worker: start with México (the usual one) so the code is rarely typed by hand
      const mexico = res.data.phone_codes.find((c) => c.iso === "MX");
      if (mexico) {
        setDefaultCodeId(String(mexico.id));
        // The code is part of what is sent, so it is chosen for real, not only shown as chosen
        if (!worker) setPhoneCodeId((previous) => previous || String(mexico.id));
      }
    }
    load();
  }, [worker]);

  // The municipalities of the saved state (editing) are loaded once; later ones when the state changes
  useEffect(() => {
    let alive = true;
    if (!state) {
      setMunicipalityNames([]);
      return;
    }
    getMunicipalities(state).then((res) => {
      if (!alive) return;
      setMunicipalitiesError(res.ok ? "" : res.error ?? "No se pudo consultar el catálogo del INEGI.");
      setMunicipalityNames(res.data?.options ?? []);
    });
    return () => {
      alive = false;
    };
  }, [state]);

  function changeState(value: string) {
    setState(value);
    setMunicipality("");
    setMunicipalityNames([]);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (feedback.localHasErrors) {
      feedback.rejectKnown();
      return;
    }

    setSubmitting(true);
    const res = await onSubmit(input);
    setSubmitting(false);

    if (!res.ok) {
      feedback.rejectResult(res);
      return;
    }

    // The worker is saved; now the photo (optional) goes up, or the old one is removed
    const savedId = res.data?.worker.id;
    if (savedId !== undefined && (photoFile || (removePhoto && worker?.photo_url))) {
      setSubmitting(true);
      const photoResult = photoFile ? await uploadWorkerPhoto(savedId, photoFile) : await deleteWorkerPhoto(savedId);
      setSubmitting(false);
      if (!photoResult.ok) {
        setPhotoWarning(
          photoResult.errors?.photo?.[0] ?? photoResult.error ?? "No se pudo guardar la fotografía."
        );
        return;
      }
    }
    onSaved();
  }

  // Dialing codes offered: the active ones, plus the ones this worker already has (even if
  // an administrator has switched them off since)
  const codeOptions = (() => {
    const list = [...(catalogs?.phone_codes ?? [])];
    const extra = [worker?.phone_code, ...(worker?.contacts ?? []).map((c) => c.phone_code)];
    for (const item of extra) {
      if (item && !list.some((c) => c.id === item.id)) list.push(item);
    }
    return list;
  })();
  const maxContacts = catalogs?.max_contacts ?? 3;

  function addContact(kind: "telefono" | "correo") {
    setContacts((rows) =>
      rows.length >= maxContacts
        ? rows
        : [
            ...rows,
            {
              key: nextRowKey.current++,
              id: null,
              kind,
              phoneCodeId: kind === "telefono" ? phoneCodeId || defaultCodeId : "",
              value: "",
              label: "",
              contactName: "",
            },
          ]
    );
  }

  function changeContact(key: number, changes: Partial<ContactRow>) {
    setContacts((rows) => rows.map((row) => (row.key === key ? { ...row, ...changes } : row)));
  }

  function removeContact(key: number) {
    setContacts((rows) => rows.filter((row) => row.key !== key));
  }

  // The placeholder of the label: the first extra phone is "Número 2" (the principal is 1)
  function labelPlaceholder(index: number) {
    const row = contacts[index];
    const before = contacts.slice(0, index).filter((r) => r.kind === row.kind).length;
    return `${row.kind === "telefono" ? "Número" : "Correo"} ${before + 2}`;
  }

  const hasSavedPhoto = !!worker?.photo_url && !removePhoto;
  const canRemovePhoto = !!photoFile || hasSavedPhoto;
  const fullName = `${firstName} ${paternalSurname}`.trim() || "la persona";

  const fieldErrors = feedback.fieldErrors;

  return (
    <form onSubmit={handleSubmit} {...feedback.formProps}>
      {generalError && <p role="alert">{generalError}</p>}
      {photoWarning && (
        <ErrorDialog
          title="El trabajador se guardó, pero no la fotografía"
          messages={[photoWarning, "Puedes volver a intentarlo editando al trabajador."]}
          onClose={onSaved}
        />
      )}

      <fieldset>
        <legend>Datos del trabajador</legend>

        <p>
          <label htmlFor="enrollment_id">Matrícula</label>
          <br />
          <input id="enrollment_id" value={enrollmentId} onChange={(e) => setEnrollmentId(e.target.value)} required />
          {fieldErrors("enrollment_id")}
        </p>
        <p>
          <label htmlFor="first_name">Nombre(s)</label>
          <br />
          <input id="first_name" value={firstName} onChange={(e) => setFirstName(e.target.value)} required />
          {fieldErrors("first_name")}
        </p>
        <p>
          <label htmlFor="paternal_surname">Apellido paterno</label>
          <br />
          <input id="paternal_surname" value={paternalSurname} onChange={(e) => setPaternalSurname(e.target.value)} required />
          {fieldErrors("paternal_surname")}
        </p>
        <p>
          <label htmlFor="maternal_surname">Apellido materno</label>
          <br />
          <input id="maternal_surname" value={maternalSurname} onChange={(e) => setMaternalSurname(e.target.value)} required />
          {fieldErrors("maternal_surname")}
        </p>
        <p>
          <label htmlFor="email">Correo electrónico</label>
          <br />
          <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          {fieldErrors("email")}
        </p>
        <p>
          <label htmlFor="phone_code_id">Código del país</label>
          <br />
          <select id="phone_code_id" value={phoneCodeId} onChange={(e) => setPhoneCodeId(e.target.value)} required>
            <option value="">---------</option>
            {codeOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          {fieldErrors("phone_code_id")}
        </p>
        <p>
          <label htmlFor="phone_number">Número telefónico</label>
          <br />
          <input id="phone_number" type="tel" inputMode="numeric" value={phoneNumber} onChange={(e) => setPhoneNumber(e.target.value)} placeholder="Solo números, sin el código" required />
          {fieldErrors("phone_number")}
        </p>
        <p>
          <label htmlFor="sex_id">Sexo</label>
          <br />
          <select id="sex_id" value={sexId} onChange={(e) => setSexId(e.target.value)} required>
            <option value="">---------</option>
            {catalogs?.sexes.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          {fieldErrors("sex_id")}
        </p>
        <p>
          <label htmlFor="role_id">Rol</label>
          <br />
          <select id="role_id" value={roleId} onChange={(e) => setRoleId(e.target.value)} required>
            <option value="">---------</option>
            {catalogs?.roles.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          {fieldErrors("role_id")}
        </p>
        <p>
          <label>
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} /> Activo
          </label>
          {fieldErrors("is_active")}
        </p>
      </fieldset>

      <fieldset>
        <legend>Otros contactos (opcional, máximo {maxContacts})</legend>
        <div className="span-all">
          <p className="hint">
            Otras formas de localizar a esta misma persona, además del teléfono y el correo de arriba: por ejemplo un
            "Número 2".
          </p>
          {contacts.length === 0 && <p>No tiene contactos adicionales.</p>}
          {contacts.map((row, index) => (
            <div className="contact-row" key={row.key} role="group" aria-label={`Contacto adicional ${index + 1}`}>
              <div>
                <label htmlFor={`contact_label_${row.key}`}>Etiqueta</label>
                <input
                  data-field="contacts"
                  id={`contact_label_${row.key}`}
                  value={row.label}
                  maxLength={40}
                  placeholder={labelPlaceholder(index)}
                  onChange={(e) => changeContact(row.key, { label: e.target.value })}
                />
              </div>
              {row.kind === "telefono" && (
                <div>
                  <label htmlFor={`contact_code_${row.key}`}>Código del país</label>
                  <select
                    data-field="contacts"
                    id={`contact_code_${row.key}`}
                    value={row.phoneCodeId}
                    onChange={(e) => changeContact(row.key, { phoneCodeId: e.target.value })}
                    required
                  >
                    <option value="">---------</option>
                    {codeOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div>
                <label htmlFor={`contact_value_${row.key}`}>{row.kind === "telefono" ? "Número telefónico" : "Correo electrónico"}</label>
                {row.kind === "telefono" ? (
                  <input
                    data-field="contacts"
                    id={`contact_value_${row.key}`}
                    type="tel"
                    inputMode="numeric"
                    placeholder="Solo números"
                    value={row.value}
                    onChange={(e) => changeContact(row.key, { value: e.target.value })}
                  />
                ) : (
                  <input
                    data-field="contacts"
                    id={`contact_value_${row.key}`}
                    type="email"
                    value={row.value}
                    onChange={(e) => changeContact(row.key, { value: e.target.value })}
                  />
                )}
              </div>
              <div>
                <label htmlFor={`contact_name_${row.key}`}>De quién es (opcional)</label>
                <input
                  data-field="contacts"
                  id={`contact_name_${row.key}`}
                  value={row.contactName}
                  maxLength={150}
                  placeholder="Ej. su esposa"
                  onChange={(e) => changeContact(row.key, { contactName: e.target.value })}
                />
              </div>
              <button type="button" onClick={() => removeContact(row.key)} aria-label={`Quitar contacto adicional ${index + 1}`}>
                Quitar
              </button>
            </div>
          ))}
          {fieldErrors("contacts")}
          <p>
            <button type="button" onClick={() => addContact("telefono")} disabled={contacts.length >= maxContacts}>
              Agregar teléfono
            </button>{" "}
            <button type="button" onClick={() => addContact("correo")} disabled={contacts.length >= maxContacts}>
              Agregar correo
            </button>
            {contacts.length >= maxContacts && <span className="hint"> Llegaste al máximo de {maxContacts} contactos.</span>}
          </p>
        </div>
      </fieldset>

      <fieldset>
        <legend>Fotografía (opcional)</legend>
        <div className="photo-field">
          <Avatar
            size="lg"
            firstName={firstName}
            paternalSurname={paternalSurname}
            enrollmentId={enrollmentId || "?"}
            photoUrl={hasSavedPhoto ? worker?.photo_url : null}
            previewUrl={photoPreview}
            label={
              photoPreview || hasSavedPhoto
                ? `Fotografía de ${fullName}`
                : `Sin fotografía: se mostrarán las iniciales de ${fullName}`
            }
          />
          <div className="photo-actions">
            <label htmlFor="photo">{canRemovePhoto ? "Cambiar fotografía" : "Elegir fotografía"}</label>
            <input
              id="photo"
              ref={photoInput}
              type="file"
              accept={PHOTO_TYPES.join(",")}
              onChange={(e) => choosePhoto(e.target.files?.[0] ?? null)}
            />
            {canRemovePhoto && (
              <button type="button" onClick={clearPhoto}>
                Quitar fotografía
              </button>
            )}
            {fieldErrors("photo")}
          </div>
        </div>
        <p className="hint">
          JPG, PNG o WebP, de hasta {PHOTO_MAX_MB} MB. Se recorta en cuadro. Si no tiene fotografía, se muestran las
          iniciales de su nombre.
        </p>
      </fieldset>

      {worker && worker.role?.label === OPERATOR_ROLE && (
        <fieldset>
          <legend>Unidades asignadas</legend>
          <div className="span-all">
            {worker.assigned_units.length === 0 ? (
              <p>No tiene unidades asignadas.</p>
            ) : (
              <ul>
                {worker.assigned_units.map((assigned) => (
                  <li key={assigned.id}>
                    {assigned.economic_number} (desde {assigned.start_date})
                  </li>
                ))}
              </ul>
            )}
            <p className="hint">Las unidades se asignan desde la pantalla de la unidad.</p>
          </div>
        </fieldset>
      )}

      {worker && worker.role?.label === MECHANIC_ROLE && (
        <fieldset>
          <legend>Reportes asignados</legend>
          <div className="span-all">
            {worker.assigned_reports.length === 0 ? (
              <p>No tiene reportes asignados.</p>
            ) : (
              <ul>
                {worker.assigned_reports.map((assigned) => (
                  <li key={assigned.id}>
                    <a href={`/reportes/${assigned.id}`}>
                      {assigned.economic_number} · {assigned.date} · {assigned.location}
                    </a>{" "}
                    (desde {assigned.start_date})
                  </li>
                ))}
              </ul>
            )}
            <p className="hint">Los reportes se asignan desde la pantalla del reporte.</p>
          </div>
        </fieldset>
      )}

      <fieldset>
        <legend>Domicilio</legend>

        <p>
          <label htmlFor="address_country">País</label>
          <br />
          <input id="address_country" value="México" readOnly />
        </p>
        <p>
          <label htmlFor="address_state">Estado</label>
          <br />
          <select
            id="address_state"
            data-field="state"
            value={state}
            onChange={(e) => changeState(e.target.value)}
            required
          >
            <option value="">---------</option>
            {stateNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          {statesError && <span className="field-error">{statesError}</span>}
          {fieldErrors("state")}
        </p>
        <p>
          <label htmlFor="address_municipality">Municipio</label>
          <br />
          <select
            id="address_municipality"
            data-field="municipality"
            value={municipality}
            onChange={(e) => setMunicipality(e.target.value)}
            required
          >
            <option value="">---------</option>
            {withCurrent(municipalityNames, state === worker?.address.state ? worker?.address.municipality ?? "" : "").map(
              (name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              )
            )}
          </select>
          {municipalitiesError && <span className="field-error">{municipalitiesError}</span>}
          {fieldErrors("municipality")}
        </p>
        <p>
          <label htmlFor="address_neighborhood">Colonia</label>
          <br />
          <input id="address_neighborhood" value={neighborhood} maxLength={150} onChange={(e) => setNeighborhood(e.target.value)} data-field="neighborhood" required />
          {fieldErrors("neighborhood")}
        </p>
        <p>
          <label htmlFor="address_street">Calle</label>
          <br />
          <input id="address_street" value={street} maxLength={150} onChange={(e) => setStreet(e.target.value)} data-field="street" required />
          {fieldErrors("street")}
        </p>
        <p>
          <label htmlFor="exterior_number">Número exterior</label>
          <br />
          <input id="exterior_number" value={exteriorNumber} onChange={(e) => setExteriorNumber(e.target.value)} required />
          {fieldErrors("exterior_number")}
        </p>
        <p>
          <label htmlFor="interior_number">Número interior (opcional)</label>
          <br />
          <input id="interior_number" value={interiorNumber} onChange={(e) => setInteriorNumber(e.target.value)} />
          {fieldErrors("interior_number")}
        </p>
      </fieldset>

      <fieldset>
        <legend>Contraseña</legend>
        <p>
          <label htmlFor="password">
            {editing ? "Nueva contraseña (déjala vacía para conservar la actual)" : "Contraseña"}
          </label>
          <br />
          <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" required={!editing} />
          <span className="hint"> {editing ? "Si la cambias, la persona tendrá que elegir otra al iniciar sesión." : "La persona tendrá que cambiarla al iniciar sesión por primera vez."}{editing && worker?.locked ? " Al guardar se desbloquea su cuenta." : ""}</span>
          {fieldErrors("password")}
        </p>
        <p>
          <label htmlFor="password_confirmation">Confirmación de contraseña</label>
          <br />
          <input id="password_confirmation" type="password" value={passwordConfirmation} onChange={(e) => setPasswordConfirmation(e.target.value)} autoComplete="new-password" required={!editing || password !== ""} />
          {fieldErrors("password_confirmation")}
        </p>
      </fieldset>

      <p>
        <button type="submit" disabled={submitting}>
          {submitting ? "Guardando..." : "Guardar"}
        </button>{" "}
        <button type="button" onClick={onCancel}>
          Cancelar
        </button>
      </p>

      {feedback.dialog}
    </form>
  );
}
