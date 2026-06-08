interface Props {
  eyebrow: string;
  title: string;
  description?: string;
}

export function SectionTitle({ eyebrow, title, description }: Props) {
  return (
    <section className="section-title">
      <div className="eyebrow">{eyebrow}</div>
      <h2>{title}</h2>
      {description ? <p>{description}</p> : null}
    </section>
  );
}
